"""
Semantic Search Integration Tests

Covers the real embedding-based semantic search in RetrievalService
and KnowledgeRetrievalService, replacing the previous hash-based
pseudo-vector approach.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from src.identity.audit import AuditService, AuditAction
from src.identity.models import User
from src.identity.rbac import Permission, RBACService
from src.knowledge.embedding import EmbeddingService
from src.knowledge.processing import ChunkMetadata, ChunkType
from src.knowledge.retrieval import (
    RetrievalService,
    SearchMode,
    SearchQuery,
    SearchResult,
)
from src.knowledge.vector_store import InMemoryVectorStore


# ── Mock RBAC that allows all ────────────────────────────────────


class MockRBAC(RBACService):
    """RBAC stub that permits all actions."""

    def __init__(self):
        pass

    def has_permission(self, user, permission) -> bool:
        return True

    async def check_permission(self, user, **kwargs) -> bool:
        return True


class MockAudit(AuditService):
    """Audit stub that swallows log calls."""

    @staticmethod
    async def log(*args, **kwargs):
        pass

    @staticmethod
    async def log_permission_denied(*args, **kwargs):
        pass


# ── Helpers ──────────────────────────────────────────────────────


def make_chunk(
    content: str,
    doc_id: Optional[str] = None,
    chunk_id: Optional[str] = None,
) -> ChunkMetadata:
    return ChunkMetadata(
        chunk_id=chunk_id or str(uuid4()),
        document_id=doc_id or str(uuid4()),
        document_version=1,
        chunk_index=0,
        chunk_type=ChunkType.PARAGRAPH,
        content=content,
        metadata={},
    )


def make_user() -> User:
    u = User()
    u.id = 1
    u.username = "test_user"
    u.is_active = True
    u.is_superuser = True
    return u


@pytest.fixture
def retrieval_service():
    """Create a RetrievalService with mock RBAC/audit and public chunks."""
    service = RetrievalService(
        rbac_service=MockRBAC(),
        audit_service=MockAudit(),
        embedding_service=EmbeddingService(provider_name="mock"),
        vector_store=InMemoryVectorStore(),
    )
    # Index some chunks with different content and register as public
    doc_ids = []
    for _ in range(4):
        doc_id = str(uuid4())
        doc_ids.append(doc_id)
        service.index_chunk(make_chunk(
            [
                "The quick brown fox jumps over the lazy dog",
                "Python is a popular programming language for data science",
                "Machine learning algorithms require large amounts of data",
                "The annual financial report shows strong revenue growth",
            ][len(doc_ids) - 1],
            doc_id=doc_id,
        ))
        service.register_document_owner(doc_id, "1", visibility="public")
    return service


# ── Tests for RetrievalService._semantic_search ──────────────────


def test_semantic_search_uses_real_embeddings(retrieval_service):
    """Semantic search should use EmbeddingService, not hash-based pseudo-vectors."""
    user = make_user()
    query = SearchQuery(query="finance report", mode=SearchMode.SEMANTIC)
    results = asyncio.run(retrieval_service.search(user, query))

    # The "finance report" chunk should be in the results
    contents = [r.chunk.content for r in results]
    finance_content = [c for c in contents if "financial report" in c]
    assert len(finance_content) > 0, (
        f"Expected 'financial report' chunk in semantic results, got: {contents}"
    )


def test_semantic_search_embeddings_indexed_once(retrieval_service):
    """_ensure_embeddings should only run once."""
    assert not retrieval_service._embeddings_indexed

    user = make_user()
    query = SearchQuery(query="test", mode=SearchMode.SEMANTIC)
    asyncio.run(retrieval_service.search(user, query))

    assert retrieval_service._embeddings_indexed
    # Vector store should have records
    assert len(retrieval_service._vector_store.records) == 4


def test_semantic_search_fallback_on_error(retrieval_service):
    """Semantic search should fall back to keyword search on error."""
    # Break the embedding service
    retrieval_service._embedding_service = None  # type: ignore

    user = make_user()
    query = SearchQuery(query="data science", mode=SearchMode.SEMANTIC)
    # Should not raise
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) > 0


def test_semantic_search_empty_query(retrieval_service):
    """Empty query should raise ValidationError."""
    user = make_user()
    query = SearchQuery(query="", mode=SearchMode.SEMANTIC)
    from src.core.errors import ValidationError

    with pytest.raises(ValidationError):
        asyncio.run(retrieval_service.search(user, query))


def test_semantic_search_no_chunks():
    """Semantic search on empty store should return empty results."""
    service = RetrievalService(
        rbac_service=MockRBAC(),
        audit_service=MockAudit(),
        embedding_service=EmbeddingService(provider_name="mock"),
        vector_store=InMemoryVectorStore(),
    )
    user = make_user()
    query = SearchQuery(query="anything", mode=SearchMode.SEMANTIC)
    results = asyncio.run(service.search(user, query))
    assert len(results) == 0


# ── Tests for RetrievalService._hybrid_search ────────────────────


def test_hybrid_search_combines_keyword_and_semantic(retrieval_service):
    """Hybrid search should return results from both keyword and semantic search."""
    user = make_user()
    query = SearchQuery(query="data science", mode=SearchMode.HYBRID)
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) > 0


def test_hybrid_search_deduplicates(retrieval_service):
    """Hybrid search should not duplicate results appearing in both methods."""
    user = make_user()
    query = SearchQuery(query="data", mode=SearchMode.HYBRID)
    results = asyncio.run(retrieval_service.search(user, query))
    chunk_ids = [r.chunk.chunk_id for r in results]
    assert len(chunk_ids) == len(set(chunk_ids)), "Hybrid search returned duplicates"


# ── Tests for SearchQuery.owner_id filter ─────────────────────────


def test_keyword_search_filters_by_owner_id(retrieval_service):
    """Keyword search with owner_id filter should return only owned documents."""
    user = make_user()
    # All chunks in fixture are registered with owner_id="1"
    query = SearchQuery(query="data", mode=SearchMode.KEYWORD, owner_id="1")
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) > 0, "owner_id='1' should return results"

    # Non-existent owner should return empty
    query = SearchQuery(query="data", mode=SearchMode.KEYWORD, owner_id="nonexistent")
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) == 0, "owner_id='nonexistent' should return empty"


def test_semantic_search_filters_by_owner_id(retrieval_service):
    """Semantic search with owner_id filter should return only owned documents."""
    user = make_user()
    query = SearchQuery(query="data science", mode=SearchMode.SEMANTIC, owner_id="1")
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) > 0, "owner_id='1' should return results"

    query = SearchQuery(query="data science", mode=SearchMode.SEMANTIC, owner_id="nonexistent")
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) == 0, "owner_id='nonexistent' should return empty"


def test_hybrid_search_filters_by_owner_id(retrieval_service):
    """Hybrid search with owner_id filter should return only owned documents."""
    user = make_user()
    query = SearchQuery(query="data science", mode=SearchMode.HYBRID, owner_id="1")
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) > 0, "owner_id='1' should return results"

    query = SearchQuery(query="data science", mode=SearchMode.HYBRID, owner_id="nonexistent")
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) == 0, "owner_id='nonexistent' should return empty"


def test_owner_id_filter_does_not_affect_default_query(retrieval_service):
    """Default owner_id=None should return all accessible documents (backward compat)."""
    user = make_user()
    query = SearchQuery(query="data", mode=SearchMode.KEYWORD)
    results = asyncio.run(retrieval_service.search(user, query))
    assert len(results) > 0, "Default owner_id=None should return results"


# ── Tests for KnowledgeRetrievalService._search_documents ─────────


@pytest.mark.asyncio
async def test_knowledge_retrieval_semantic_strategy():
    """KnowledgeRetrievalService._search_documents should respect SEMANTIC strategy."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from src.database.base import Base
    from src.database.models import DocumentModel
    from src.knowledge.knowledge_retrieval import (
        KnowledgeQuery,
        KnowledgeRetrievalService,
        KnowledgeSource,
        SearchStrategy,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Insert a test document
        doc = DocumentModel(
            id=str(uuid4()),
            filename="test_report.txt",
            title="Q1 Sales Report",
            file_type="txt",
            size=512,
            content="The Q1 sales report shows strong revenue growth in the enterprise segment.",
            tags=["sales", "quarterly"],
            meta={"department": "sales"},
            created_by="1",
            status="available",
        )
        session.add(doc)
        await session.commit()

        rbac = MockRBAC()
        audit = MockAudit()

        service = KnowledgeRetrievalService(
            session=session,
            rbac_service=rbac,
            audit_service=audit,
            embedding_service=EmbeddingService(provider_name="mock"),
        )

        user = make_user()
        query = KnowledgeQuery(
            query="revenue growth",
            sources=[KnowledgeSource.DOCUMENT],
            strategy=SearchStrategy.SEMANTIC,
        )
        results = await service.search(user, query)
        assert len(results) > 0, "Semantic search should return results"
        assert results[0].source == KnowledgeSource.DOCUMENT


@pytest.mark.asyncio
async def test_knowledge_retrieval_hybrid_strategy():
    """KnowledgeRetrievalService._search_documents should respect HYBRID strategy."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from src.database.base import Base
    from src.database.models import DocumentModel
    from src.knowledge.knowledge_retrieval import (
        KnowledgeQuery,
        KnowledgeRetrievalService,
        KnowledgeSource,
        SearchStrategy,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Insert a test document
        doc = DocumentModel(
            id=str(uuid4()),
            filename="budget_plan.txt",
            title="2026 Budget Plan",
            file_type="txt",
            size=512,
            content="The 2026 budget plan allocates funding for AI and machine learning initiatives.",
            tags=["budget", "planning"],
            meta={"department": "finance"},
            created_by="1",
            status="available",
        )
        session.add(doc)
        await session.commit()

        rbac = MockRBAC()
        audit = MockAudit()

        service = KnowledgeRetrievalService(
            session=session,
            rbac_service=rbac,
            audit_service=audit,
            embedding_service=EmbeddingService(provider_name="mock"),
        )

        user = make_user()
        query = KnowledgeQuery(
            query="budget AI",
            sources=[KnowledgeSource.DOCUMENT],
            strategy=SearchStrategy.HYBRID,
        )
        results = await service.search(user, query)
        assert len(results) > 0, "Hybrid search should return results"
        assert results[0].source == KnowledgeSource.DOCUMENT