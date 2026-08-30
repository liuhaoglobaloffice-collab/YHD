"""P2-6 Embedding persistence tests (Gap 11 + 12).

Verifies that the EmbeddingPipeline with an EmbeddingStorageRepository:
- persists embedding results to EmbeddingStorageModel (real SQLite session)
- skips duplicate ingestion (idempotency via repository + vector store)
- rolls back the DB session on embedding failure (no partial success records)
- keeps the vector store and DB records consistent

No real LLM is called — the mock provider provides deterministic vectors.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.database.models import EmbeddingStorageModel
from src.database.repositories.knowledge import EmbeddingStorageRepository
from src.knowledge.chunker import Chunk
from src.knowledge.embedding import EmbeddingError, EmbeddingPipeline
from src.knowledge.vector_store import InMemoryVectorStore


def make_chunks(document_id="doc-p1", count=3):
    return [
        Chunk(
            chunk_id=f"{document_id}_chunk_{i}",
            document_id=document_id,
            content=f"Chunk {i} content about topic {i}.",
            chunk_index=i,
        )
        for i in range(count)
    ]


async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def make_pipeline(store=None, session_factory=None):
    store = store or InMemoryVectorStore()
    session = session_factory()
    repo = EmbeddingStorageRepository(session)
    pipeline = EmbeddingPipeline(
        vector_store=store,
        provider_name="mock",
        storage_repository=repo,
    )
    return store, session, repo, pipeline


# ======================================================================
# Embedding persistence
# ======================================================================


@pytest.mark.asyncio
async def test_embedding_persisted_to_embedding_storage_model():
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    result = await pipeline.run_chunks(make_chunks())

    assert result["storage_status"] == "ok"
    assert result["embeddings_created"] == 3

    records = await repo.find_by_document("doc-p1")
    assert len(records) == 3
    for record in records:
        assert record.vector == [0.1, 0.2, 0.3]  # mock provider vector
        assert record.dimension == 3
        assert record.provider == "mock"
        assert record.document_id == "doc-p1"
        assert record.chunk_id.startswith("doc-p1_chunk_")
    await session.close()


@pytest.mark.asyncio
async def test_document_chunk_embedding_relationship_consistency():
    """Every chunk produces exactly one DB record and one vector store entry."""
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    chunks = make_chunks()
    await pipeline.run_chunks(chunks)

    records = await repo.find_by_document("doc-p1")
    assert {r.chunk_id for r in records} == {c.chunk_id for c in chunks}
    assert len(store.records) == len(chunks)
    assert {r.chunk_id for r in store.records} == {c.chunk_id for c in chunks}
    await session.close()


# ======================================================================
# Duplicate ingestion
# ======================================================================


@pytest.mark.asyncio
async def test_duplicate_ingestion_skips_existing_records():
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    chunks = make_chunks()
    result1 = await pipeline.run_chunks(chunks)
    assert result1["embeddings_created"] == 3
    assert result1["embeddings_skipped"] == 0

    # Re-ingest the same chunks: repository records exist → all skipped
    result2 = await pipeline.run_chunks(chunks)
    assert result2["embeddings_created"] == 0
    assert result2["embeddings_skipped"] == 3

    # Still exactly one record per chunk (no duplicates)
    records = await repo.find_by_document("doc-p1")
    assert len(records) == 3
    await session.close()


@pytest.mark.asyncio
async def test_duplicate_ingestion_via_run_text_is_idempotent():
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    text = "Alpha beta gamma delta epsilon zeta. " * 3
    result1 = await pipeline.run(document_id="doc-t1", text=text)
    result2 = await pipeline.run(document_id="doc-t1", text=text)

    assert result1["embeddings_created"] >= 1
    assert result2["embeddings_skipped"] == result1["embeddings_created"]

    records = await repo.find_by_document("doc-t1")
    assert len(records) == result1["embeddings_created"]
    await session.close()


@pytest.mark.asyncio
async def test_vector_store_only_existing_chunks_skipped_without_repo():
    """Without a repository, skip_existing still works via vector store."""
    store = InMemoryVectorStore()
    pipeline = EmbeddingPipeline(vector_store=store, provider_name="mock")

    text = "Some persistent text for chunking."
    result1 = await pipeline.run(document_id="doc-v1", text=text)
    result2 = await pipeline.run(document_id="doc-v1", text=text)
    assert result1["embeddings_created"] >= 1
    assert result2["embeddings_skipped"] == result1["embeddings_created"]


# ======================================================================
# Embedding failure and rollback
# ======================================================================


@pytest.mark.asyncio
async def test_embedding_failure_rolls_back_transaction():
    """A failing embed must leave no partial success records in the DB."""
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    chunks = make_chunks(count=3)
    call_count = {"n": 0}

    original_embed = pipeline.embedding_service.embed_text

    async def flaky_embed(text, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:  # fail on the second chunk
            raise EmbeddingError("provider down")
        return await original_embed(text, **kwargs)

    with patch.object(pipeline.embedding_service, "embed_text", side_effect=flaky_embed):
        with pytest.raises(EmbeddingError, match="provider down"):
            await pipeline.run_chunks(chunks)

    # Rollback happened and no records were committed
    records = await repo.find_by_document("doc-p1")
    assert records == []
    await session.close()


@pytest.mark.asyncio
async def test_embedding_failure_no_success_record_for_failed_chunk():
    """The failing chunk itself must not have a DB record."""
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    async def always_fail(text, **kwargs):
        raise EmbeddingError("connection refused")

    with patch.object(pipeline.embedding_service, "embed_text", side_effect=always_fail):
        with pytest.raises(EmbeddingError):
            await pipeline.run_chunks(make_chunks(count=1))

    record = await repo.find_by_chunk("doc-p1_chunk_0")
    assert record is None
    await session.close()


@pytest.mark.asyncio
async def test_rollback_after_partial_upsert():
    """Even after a successful upsert flush, a later failure rolls everything back."""
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    chunks = make_chunks(count=3)
    embeds = {"n": 0}

    original_embed = pipeline.embedding_service.embed_text

    async def fail_on_third(text, **kwargs):
        embeds["n"] += 1
        if embeds["n"] >= 3:
            raise EmbeddingError("timeout on third chunk")
        return await original_embed(text, **kwargs)

    with patch.object(pipeline.embedding_service, "embed_text", side_effect=fail_on_third):
        with pytest.raises(EmbeddingError):
            await pipeline.run_chunks(chunks)

    # First two chunks were upserted (flushed) but the failure rolled back all
    records = await repo.find_by_document("doc-p1")
    assert records == []
    await session.close()


# ======================================================================
# Vector store consistency
# ======================================================================


@pytest.mark.asyncio
async def test_vector_store_and_db_consistent_after_success():
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    await pipeline.run_chunks(make_chunks())

    records = await repo.find_by_document("doc-p1")
    for record in records:
        assert store.has_chunk(record.chunk_id)

    for vs_record in store.records:
        db_record = await repo.find_by_chunk(vs_record.chunk_id)
        assert db_record is not None
        assert db_record.vector == vs_record.embedding
    await session.close()


@pytest.mark.asyncio
async def test_search_still_works_with_storage_repository():
    """VectorStore retrieval capability is preserved."""
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    await pipeline.run_chunks(make_chunks())

    results = await pipeline.search("Chunk 1 content", limit=5)
    assert len(results) >= 1
    assert results[0]["document_id"] == "doc-p1"
    await session.close()


@pytest.mark.asyncio
async def test_upsert_updates_existing_record_on_reembed():
    """Re-embedding with skip_existing=False updates instead of duplicating."""
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    chunks = make_chunks(count=1)
    await pipeline.run_chunks(chunks, skip_existing=True)
    await pipeline.run_chunks(chunks, skip_existing=False)

    records = await repo.find_by_document("doc-p1")
    assert len(records) == 1  # unique constraint: updated, not duplicated
    await session.close()


@pytest.mark.asyncio
async def test_run_chunks_empty_list_is_noop():
    session_factory = await _make_session()
    store, session, repo, pipeline = make_pipeline(session_factory=session_factory)

    result = await pipeline.run_chunks([])
    assert result["chunks_count"] == 0
    assert result["embeddings_created"] == 0
    assert result["storage_status"] == "noop"
    await session.close()
