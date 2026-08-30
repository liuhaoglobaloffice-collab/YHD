"""P0-2 Knowledge persistence tests.

Verifies the real database persistence chain:

    Document (DB) → Chunks (DB) → Embeddings (DB + SQLiteVectorStore)
        → Retrieval (restart-safe)

Coverage:
1.  Document DB persistence (upload → DocumentModel row)
2.  Document restart persistence (new session/service instance)
3.  Chunk persistence (DocumentChunkModel rows)
4.  Embedding persistence (EmbeddingStorageModel rows + vector store)
5.  Embedding idempotency (re-index replaces, no unbounded duplicates)
6.  Embedding rollback (failure leaves no half-finished state)
7.  Semantic retrieval DB-backed
8.  Hybrid retrieval DB-backed
9.  Restart recovery (load_persisted rebuilds index; vectors survive)
10. Tenant isolation (documents: get/list; search: keyword/semantic/hybrid)
11. Permission isolation (missing KNOWLEDGE_READ/WRITE → denied)
12. Missing document → NotFoundError
13. Invalid document → ValidationError
14. Duplicate upload → new version + parent archived
15. Delete document → archived (soft delete)

All tests use real SQLite sessions (aiosqlite) and a file-backed
SQLiteVectorStore; no in-memory stand-ins for the persistence layer.
The mock LLM provider supplies deterministic embedding vectors.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from src.database.base import Base
from src.database.models import DocumentChunkModel, DocumentModel, EmbeddingStorageModel
from src.database.repositories.knowledge import (
    DocumentChunkRepository,
    EmbeddingStorageRepository,
)
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import RBACService
from src.knowledge.documents import DocumentService, DocumentStatus
from src.knowledge.embedding import EmbeddingError, EmbeddingService
from src.knowledge.processing import ChunkMetadata, ChunkType
from src.knowledge.retrieval import RetrievalService, SearchMode, SearchQuery
from src.knowledge.vector_store import SQLiteVectorStore
from src.security.policy import PolicyEngine


# ── Mock audit (static class, no-op) ─────────────────────────────


class MockAudit(AuditService):
    """Audit stub that swallows log calls (no DB writes in tests)."""

    @staticmethod
    async def log(*args, **kwargs):
        pass

    @staticmethod
    async def log_permission_denied(*args, **kwargs):
        pass


# ── Helpers ──────────────────────────────────────────────────────


async def make_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def make_user(user_id=1, superuser=True, perm_config=None):
    u = User()
    u.id = user_id
    u.username = f"user_{user_id}"
    u.is_active = True
    u.is_superuser = superuser
    u.role = None
    u.permissions_config = perm_config
    return u


def make_chunks(document_id, contents, owner_id="1", visibility="private"):
    return [
        ChunkMetadata(
            chunk_id=f"{document_id}_chunk_{i}",
            document_id=document_id,
            document_version=1,
            chunk_index=i,
            chunk_type=ChunkType.PARAGRAPH,
            content=content,
            metadata={
                "owner_id": owner_id,
                "visibility": visibility,
                "file_type": "text/plain",
            },
        )
        for i, content in enumerate(contents)
    ]


def make_doc_service(session):
    return DocumentService(
        rbac_service=RBACService(session),
        policy_engine=PolicyEngine(),
        audit_service=MockAudit,
        session=session,
    )


def make_retrieval_service(session, vector_store):
    return RetrievalService(
        rbac_service=RBACService(session),
        audit_service=MockAudit,
        embedding_service=EmbeddingService(provider_name="mock"),
        vector_store=vector_store,
        session=session,
        chunk_repository=DocumentChunkRepository(session),
        embedding_repository=EmbeddingStorageRepository(session),
    )


DOC_CONTENT = b"Machine learning transforms raw data into predictive insights. " * 4


# ======================================================================
# 1-2. Document DB persistence + restart persistence
# ======================================================================


@pytest.mark.asyncio
async def test_document_upload_persists_to_db():
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)
        user = make_user(1)

        doc = await svc.upload_document(
            user=user,
            filename="report.txt",
            file_type="text/plain",
            size=len(DOC_CONTENT),
            content=DOC_CONTENT,
        )

        result = await session.execute(
            select(DocumentModel).where(DocumentModel.id == doc.id)
        )
        model = result.scalar_one()
        assert model.filename == "report.txt"
        assert model.file_type == "text/plain"
        assert model.size == len(DOC_CONTENT)
        assert model.created_by == "1"
        assert model.status == DocumentStatus.UPLOADED.value
        assert model.content_hash == doc.hash
        assert model.content is not None and len(model.content) > 0
        assert model.meta["content_hash"] == doc.hash
        assert model.meta["source"] == "upload"


@pytest.mark.asyncio
async def test_document_survives_new_session_restart():
    """Create in one session; read back in a brand-new session."""
    session_factory = await make_session_factory()

    doc_id = None
    async with session_factory() as session:
        svc = make_doc_service(session)
        doc = await svc.upload_document(
            user=make_user(1),
            filename="restart.txt",
            file_type="text/plain",
            size=len(DOC_CONTENT),
            content=DOC_CONTENT,
        )
        doc_id = doc.id

    async with session_factory() as session:  # "restart"
        svc = make_doc_service(session)
        fetched = await svc.get_document(user=make_user(1), document_id=doc_id)
        assert fetched.id == doc_id
        assert fetched.filename == "restart.txt"

        listed = await svc.list_documents(user=make_user(1))
        assert any(d.id == doc_id for d in listed)


@pytest.mark.asyncio
async def test_document_update_status_persists():
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)
        doc = await svc.upload_document(
            user=make_user(1),
            filename="status.txt",
            file_type="text/plain",
            size=len(DOC_CONTENT),
            content=DOC_CONTENT,
        )

        await svc.update_status(doc.id, DocumentStatus.INDEXED)

    async with session_factory() as session:
        result = await session.execute(
            select(DocumentModel).where(DocumentModel.id == doc.id)
        )
        model = result.scalar_one()
        assert model.status == DocumentStatus.INDEXED.value


@pytest.mark.asyncio
async def test_document_delete_archives_in_db():
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)
        doc = await svc.upload_document(
            user=make_user(1),
            filename="del.txt",
            file_type="text/plain",
            size=len(DOC_CONTENT),
            content=DOC_CONTENT,
        )
        await svc.delete_document(user=make_user(1), document_id=doc.id)

    async with session_factory() as session:
        result = await session.execute(
            select(DocumentModel).where(DocumentModel.id == doc.id)
        )
        model = result.scalar_one()
        assert model.status == DocumentStatus.ARCHIVED.value


@pytest.mark.asyncio
async def test_duplicate_upload_creates_new_version():
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)
        user = make_user(1)

        doc1 = await svc.upload_document(
            user=user,
            filename="v1.txt",
            file_type="text/plain",
            size=len(DOC_CONTENT),
            content=DOC_CONTENT,
        )
        doc2 = await svc.upload_document(
            user=user,
            filename="v2.txt",
            file_type="text/plain",
            size=len(DOC_CONTENT),
            content=DOC_CONTENT,  # same content → same hash
        )

        assert doc2.version == 2
        assert doc2.parent_id == doc1.id

        # Parent is archived in the DB
        result = await session.execute(
            select(DocumentModel).where(DocumentModel.id == doc1.id)
        )
        parent = result.scalar_one()
        assert parent.status == DocumentStatus.ARCHIVED.value


# ======================================================================
# 3-6. Chunk + embedding persistence, idempotency, rollback
# ======================================================================


@pytest.mark.asyncio
async def test_index_chunks_persisted_writes_chunks_and_embeddings(tmp_path):
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))

    async with session_factory() as session:
        # Parent document must exist (FK constraint)
        session.add(
            DocumentModel(
                id="doc-1",
                filename="a.txt",
                file_type="text/plain",
                size=10,
                created_by="1",
                status="uploaded",
            )
        )
        await session.commit()

        svc = make_retrieval_service(session, store)
        chunks = make_chunks(
            "doc-1",
            ["Alpha topic one.", "Beta topic two.", "Gamma topic three."],
        )

        result = await svc.index_chunks_persisted(chunks)

        assert result["chunks_count"] == 3
        assert result["embeddings_created"] == 3

        chunk_rows = (
            (await session.execute(select(DocumentChunkModel))).scalars().all()
        )
        assert len(chunk_rows) == 3
        assert {c.document_id for c in chunk_rows} == {"doc-1"}

        embed_rows = (
            (await session.execute(select(EmbeddingStorageModel))).scalars().all()
        )
        assert len(embed_rows) == 3
        assert all(r.provider == "mock" for r in embed_rows)
        assert all(r.document_id == "doc-1" for r in embed_rows)

        assert len(store.records) == 3


@pytest.mark.asyncio
async def test_reindex_is_idempotent_no_duplicates(tmp_path):
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))

    async with session_factory() as session:
        session.add(
            DocumentModel(
                id="doc-1",
                filename="a.txt",
                file_type="text/plain",
                size=10,
                created_by="1",
                status="uploaded",
            )
        )
        await session.commit()

        svc = make_retrieval_service(session, store)
        chunks = make_chunks("doc-1", ["Alpha one.", "Beta two."])

        await svc.index_chunks_persisted(chunks)
        await svc.index_chunks_persisted(chunks)  # re-index

        chunk_rows = (
            (await session.execute(select(DocumentChunkModel))).scalars().all()
        )
        embed_rows = (
            (await session.execute(select(EmbeddingStorageModel))).scalars().all()
        )
        assert len(chunk_rows) == 2, "re-index must replace, not duplicate"
        assert len(embed_rows) == 2
        assert len(store.records) == 2


@pytest.mark.asyncio
async def test_embedding_failure_rolls_back_chunks(tmp_path):
    """Embedding failure must leave NO chunks and NO embeddings (all-or-nothing)."""
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))

    async with session_factory() as session:
        session.add(
            DocumentModel(
                id="doc-1",
                filename="a.txt",
                file_type="text/plain",
                size=10,
                created_by="1",
                status="uploaded",
            )
        )
        await session.commit()

        svc = make_retrieval_service(session, store)
        chunks = make_chunks("doc-1", ["Alpha one.", "Beta two.", "Gamma three."])

        # Patch at class level: index_chunks_persisted builds an
        # EmbeddingPipeline with its own internal EmbeddingService.
        async def failing_embed(self, text, **kwargs):
            raise EmbeddingError("provider down")

        with patch.object(EmbeddingService, "embed_text", failing_embed):
            with pytest.raises(EmbeddingError):
                await svc.index_chunks_persisted(chunks)

        # Rollback: no chunks, no embeddings, no vectors
        chunk_rows = (
            (await session.execute(select(DocumentChunkModel))).scalars().all()
        )
        embed_rows = (
            (await session.execute(select(EmbeddingStorageModel))).scalars().all()
        )
        assert chunk_rows == [], "chunks must be rolled back on embedding failure"
        assert embed_rows == [], "embeddings must be rolled back on failure"
        assert store.records == []


@pytest.mark.asyncio
async def test_missing_document_raises_not_found():
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)
        with pytest.raises(NotFoundError):
            await svc.get_document(user=make_user(1), document_id="no-such-doc")


@pytest.mark.asyncio
async def test_invalid_file_type_rejected():
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)
        with pytest.raises(ValidationError):
            await svc.upload_document(
                user=make_user(1),
                filename="evil.exe",
                file_type="application/x-msdownload",
                size=100,
                content=b"MZ...",
            )


@pytest.mark.asyncio
async def test_db_failure_propagates_no_silent_success():
    """A DB failure during upload must raise, not silently succeed."""
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)

        async def failing_execute(*args, **kwargs):
            raise RuntimeError("database unavailable")

        with patch.object(session, "execute", side_effect=failing_execute):
            # repository.create → session.execute fails
            with pytest.raises(RuntimeError):
                await svc.upload_document(
                    user=make_user(1),
                    filename="dbfail.txt",
                    file_type="text/plain",
                    size=len(DOC_CONTENT),
                    content=DOC_CONTENT,
                )


# ======================================================================
# 7-9. Retrieval DB-backed + restart recovery
# ======================================================================


async def _index_docs(session_factory, store):
    """Index two documents for two owners inside one session."""
    async with session_factory() as session:
        for doc_id, owner in (("doc-a", "1"), ("doc-b", "2")):
            session.add(
                DocumentModel(
                    id=doc_id,
                    filename=f"{doc_id}.txt",
                    file_type="text/plain",
                    size=10,
                    created_by=owner,
                    status="indexed",
                )
            )
        await session.commit()

        svc = make_retrieval_service(session, store)
        await svc.index_chunks_persisted(
            make_chunks("doc-a", ["Quarterly revenue growth is strong."], owner_id="1")
        )
        await svc.index_chunks_persisted(
            make_chunks("doc-b", ["Kitchen renovation tips and tricks."], owner_id="2")
        )


@pytest.mark.asyncio
async def test_semantic_search_db_backed(tmp_path):
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))
    await _index_docs(session_factory, store)

    async with session_factory() as session:
        svc = make_retrieval_service(session, store)
        await svc.load_persisted()  # new session → restore index from DB
        results = await svc.search(
            user=make_user(1),
            query=SearchQuery(query="revenue growth", mode=SearchMode.SEMANTIC),
        )
        assert len(results) > 0
        assert any("revenue" in r.chunk.content for r in results)


@pytest.mark.asyncio
async def test_hybrid_search_db_backed(tmp_path):
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))
    await _index_docs(session_factory, store)

    async with session_factory() as session:
        svc = make_retrieval_service(session, store)
        await svc.load_persisted()  # new session → restore index from DB
        results = await svc.search(
            user=make_user(1),
            query=SearchQuery(query="revenue", mode=SearchMode.HYBRID),
        )
        assert len(results) > 0


@pytest.mark.asyncio
async def test_keyword_search_db_backed(tmp_path):
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))
    await _index_docs(session_factory, store)

    async with session_factory() as session:
        svc = make_retrieval_service(session, store)
        await svc.load_persisted()  # new session → restore index from DB
        results = await svc.search(
            user=make_user(1),
            query=SearchQuery(query="revenue", mode=SearchMode.KEYWORD),
        )
        assert len(results) > 0


@pytest.mark.asyncio
async def test_restart_recovery_full_chain(tmp_path):
    """Core acceptance: new service instance + new session + new vector store
    instance pointing at the same DB file → knowledge still retrievable."""
    session_factory = await make_session_factory()
    db_path = str(tmp_path / "vec.db")
    await _index_docs(session_factory, SQLiteVectorStore(db_path=db_path))

    # ── Simulated restart: brand-new instances ──
    async with session_factory() as session:
        fresh_store = SQLiteVectorStore(db_path=db_path)
        svc = make_retrieval_service(session, fresh_store)

        restored = await svc.load_persisted()
        assert restored == 2, "both chunks must be restored from the DB"

        for mode in (SearchMode.KEYWORD, SearchMode.SEMANTIC, SearchMode.HYBRID):
            results = await svc.search(
                user=make_user(1),
                query=SearchQuery(query="revenue growth", mode=mode),
            )
            assert len(results) > 0, f"{mode} search must work after restart"
            assert all("revenue" in r.chunk.content for r in results)


@pytest.mark.asyncio
async def test_restart_does_not_reembed(tmp_path):
    """After load_persisted, semantic search must NOT re-embed chunks
    (embeddings already live in the persistent vector store)."""
    session_factory = await make_session_factory()
    db_path = str(tmp_path / "vec.db")
    await _index_docs(session_factory, SQLiteVectorStore(db_path=db_path))

    async with session_factory() as session:
        svc = make_retrieval_service(session, SQLiteVectorStore(db_path=db_path))
        await svc.load_persisted()
        assert svc._embeddings_indexed, "restored service must not re-embed"

        embed_calls = {"n": 0}
        original = svc._embedding_service.embed_text

        async def counting_embed(text, **kwargs):
            embed_calls["n"] += 1
            return await original(text, **kwargs)

        with patch.object(
            svc._embedding_service, "embed_text", side_effect=counting_embed
        ):
            await svc.search(
                user=make_user(1),
                query=SearchQuery(query="revenue", mode=SearchMode.SEMANTIC),
            )
        # Only the query itself is embedded (1 call), not the 2 chunks
        assert embed_calls["n"] == 1


# ======================================================================
# 10-11. Tenant isolation + permission isolation
# ======================================================================


@pytest.mark.asyncio
async def test_document_tenant_isolation_get_and_list():
    """Non-admin user B cannot get or list user A's documents."""
    session_factory = await make_session_factory()
    user_a = make_user(1)
    # User B: has knowledge permissions but is neither superuser nor admin
    user_b = make_user(
        2, superuser=False, perm_config={"knowledge:read": True, "knowledge:write": True}
    )

    async with session_factory() as session:
        svc = make_doc_service(session)
        doc = await svc.upload_document(
            user=user_a,
            filename="secret.txt",
            file_type="text/plain",
            size=len(DOC_CONTENT),
            content=DOC_CONTENT,
        )

        # B cannot get A's document
        with pytest.raises(PermissionDeniedError):
            await svc.get_document(user=user_b, document_id=doc.id)

        # B's list does not contain A's document
        b_docs = await svc.list_documents(user=user_b)
        assert all(d.id != doc.id for d in b_docs)

        # A still sees their own document
        a_docs = await svc.list_documents(user=user_a)
        assert any(d.id == doc.id for d in a_docs)


@pytest.mark.asyncio
async def test_search_tenant_isolation_all_modes(tmp_path):
    """User B's keyword/semantic/hybrid searches must not return A's private docs."""
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))
    await _index_docs(session_factory, store)

    user_a = make_user(1)
    user_b = make_user(
        2, superuser=False, perm_config={"knowledge:read": True, "knowledge:write": True}
    )

    async with session_factory() as session:
        svc = make_retrieval_service(session, store)
        await svc.load_persisted()

        for mode in (SearchMode.KEYWORD, SearchMode.SEMANTIC, SearchMode.HYBRID):
            b_results = await svc.search(
                user=user_b,
                query=SearchQuery(query="revenue growth", mode=mode),
            )
            # B may see their OWN docs, but never A's private documents
            assert all(
                r.chunk.document_id != "doc-a" for r in b_results
            ), f"user B must not see A's docs via {mode}"

            a_results = await svc.search(
                user=user_a,
                query=SearchQuery(query="revenue growth", mode=mode),
            )
            assert len(a_results) > 0, f"user A must see own docs via {mode}"
            assert all(
                r.chunk.document_id != "doc-b" for r in a_results
            ), f"user A must not see B's docs via {mode}"


@pytest.mark.asyncio
async def test_permission_denied_without_knowledge_read():
    session_factory = await make_session_factory()
    no_perm_user = make_user(3, superuser=False, perm_config={"knowledge:read": False})

    async with session_factory() as session:
        doc_svc = make_doc_service(session)
        with pytest.raises(PermissionDeniedError):
            await doc_svc.get_document(user=no_perm_user, document_id="any")

        retrieval_svc = make_retrieval_service(session, SQLiteVectorStore())
        with pytest.raises(PermissionDeniedError):
            await retrieval_svc.search(
                user=no_perm_user,
                query=SearchQuery(query="anything"),
            )


@pytest.mark.asyncio
async def test_permission_denied_without_knowledge_write():
    session_factory = await make_session_factory()
    no_write_user = make_user(4, superuser=False, perm_config={"knowledge:write": False})

    async with session_factory() as session:
        svc = make_doc_service(session)
        with pytest.raises(PermissionDeniedError):
            await svc.upload_document(
                user=no_write_user,
                filename="x.txt",
                file_type="text/plain",
                size=10,
                content=b"hello",
            )


# ======================================================================
# Security policy integration
# ======================================================================


def test_policy_engine_has_knowledge_document_policy():
    """The knowledge_document policy must exist and default to ALLOW
    (RBAC handles the fine-grained security)."""
    engine = PolicyEngine()
    decision = engine.evaluate(
        resource="knowledge_document", action="upload_document", context={}
    )
    assert decision.is_allowed()


def test_policy_engine_denies_disabled_knowledge_document():
    engine = PolicyEngine()
    engine._policies["knowledge_document"]["enabled"] = False
    decision = engine.evaluate(
        resource="knowledge_document", action="upload_document", context={}
    )
    assert not decision.is_allowed()


@pytest.mark.asyncio
async def test_upload_blocked_when_policy_disabled():
    session_factory = await make_session_factory()
    async with session_factory() as session:
        svc = make_doc_service(session)
        svc.policy._policies["knowledge_document"]["enabled"] = False

        with pytest.raises(PermissionDeniedError):
            await svc.upload_document(
                user=make_user(1),
                filename="blocked.txt",
                file_type="text/plain",
                size=10,
                content=b"blocked",
            )


# ======================================================================
# remove_document_chunks_persisted (full cleanup)
# ======================================================================


@pytest.mark.asyncio
async def test_remove_document_chunks_cleans_all_stores(tmp_path):
    session_factory = await make_session_factory()
    store = SQLiteVectorStore(db_path=str(tmp_path / "vec.db"))

    async with session_factory() as session:
        session.add(
            DocumentModel(
                id="doc-1",
                filename="a.txt",
                file_type="text/plain",
                size=10,
                created_by="1",
                status="uploaded",
            )
        )
        await session.commit()

        svc = make_retrieval_service(session, store)
        await svc.index_chunks_persisted(
            make_chunks("doc-1", ["Alpha one.", "Beta two."])
        )

        removed = await svc.remove_document_chunks_persisted("doc-1")
        assert removed == 2

        chunk_rows = (
            (await session.execute(select(DocumentChunkModel))).scalars().all()
        )
        embed_rows = (
            (await session.execute(select(EmbeddingStorageModel))).scalars().all()
        )
        assert chunk_rows == []
        assert embed_rows == []
        assert store.records == []
        assert len(svc._chunks) == 0
