"""
Tests for Knowledge Retrieval
"""

import pytest

from src.core.errors import ValidationError
from src.identity.models import RoleEnum, User
from src.identity.rbac import Permission
from src.knowledge.processing import ChunkMetadata, ChunkType
from src.knowledge.retrieval import (
    RetrievalService,
    SearchMode,
    SearchQuery,
)


@pytest.fixture
def regular_user():
    """Regular user fixture"""
    return User(
        id=1,
        username="testuser",
        email="user@test.com",
        hashed_password="hashed",
        role=RoleEnum.USER,
        is_active=True,
    )


@pytest.fixture
def mock_rbac():
    """Mock RBAC service"""

    class MockRBAC:
        def has_permission(self, user, permission):
            if permission == Permission.KNOWLEDGE_READ:
                return True
            return False

    return MockRBAC()


@pytest.fixture
def mock_audit():
    """Mock audit service"""

    class MockAudit:
        async def log(self, action, user_id, resource_type, resource_id=None, details=None):
            pass

        async def log_permission_denied(self, user_id, action, resource_type, resource_id=None):
            pass

    return MockAudit()


@pytest.fixture
def retrieval_service(mock_rbac, mock_audit):
    """Retrieval service fixture"""
    return RetrievalService(
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    )


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing"""
    return [
        ChunkMetadata(
            chunk_id="chunk1",
            document_id="doc1",
            document_version=1,
            chunk_index=0,
            chunk_type=ChunkType.PARAGRAPH,
            content="Python is a programming language.",
        ),
        ChunkMetadata(
            chunk_id="chunk2",
            document_id="doc1",
            document_version=1,
            chunk_index=1,
            chunk_type=ChunkType.PARAGRAPH,
            content="JavaScript is also a programming language.",
        ),
        ChunkMetadata(
            chunk_id="chunk3",
            document_id="doc2",
            document_version=1,
            chunk_index=0,
            chunk_type=ChunkType.PARAGRAPH,
            content="Machine learning is a subset of artificial intelligence.",
        ),
    ]


class TestRetrievalService:
    """Test RetrievalService"""

    def test_index_chunk(self, retrieval_service):
        """Test indexing a chunk"""
        chunk = ChunkMetadata(
            chunk_id="chunk1",
            document_id="doc1",
            document_version=1,
            chunk_index=0,
            chunk_type=ChunkType.PARAGRAPH,
            content="Test content",
        )

        retrieval_service.index_chunk(chunk)
        assert "chunk1" in retrieval_service._chunks

    def test_index_chunks(self, retrieval_service, sample_chunks):
        """Test indexing multiple chunks"""
        retrieval_service.index_chunks(sample_chunks)

        assert len(retrieval_service._chunks) == 3
        assert "chunk1" in retrieval_service._chunks
        assert "chunk2" in retrieval_service._chunks
        assert "chunk3" in retrieval_service._chunks

    @pytest.mark.asyncio
    async def test_keyword_search(self, retrieval_service, regular_user, sample_chunks):
        """Test keyword search"""
        retrieval_service.index_chunks(sample_chunks)

        query = SearchQuery(
            query="programming language",
            mode=SearchMode.KEYWORD,
        )

        results = await retrieval_service.search(regular_user, query)

        assert len(results) > 0
        assert any("programming" in r.chunk.content.lower() for r in results)

    @pytest.mark.asyncio
    async def test_search_with_filters(self, retrieval_service, regular_user, sample_chunks):
        """Test search with document filter"""
        retrieval_service.index_chunks(sample_chunks)

        query = SearchQuery(
            query="programming",
            mode=SearchMode.KEYWORD,
            document_ids=["doc1"],
        )

        results = await retrieval_service.search(regular_user, query)

        assert all(r.chunk.document_id == "doc1" for r in results)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, retrieval_service, regular_user):
        """Test search with empty query"""
        query = SearchQuery(query="")

        with pytest.raises(ValidationError):
            await retrieval_service.search(regular_user, query)

    @pytest.mark.asyncio
    async def test_get_chunk(self, retrieval_service, regular_user, sample_chunks):
        """Test get chunk by ID"""
        retrieval_service.index_chunks(sample_chunks)

        chunk = await retrieval_service.get_chunk(regular_user, "chunk1")
        assert chunk.chunk_id == "chunk1"

    def test_remove_document_chunks(self, retrieval_service, sample_chunks):
        """Test removing document chunks"""
        retrieval_service.index_chunks(sample_chunks)

        removed = retrieval_service.remove_document_chunks("doc1")
        assert removed == 2  # chunk1 and chunk2

        assert "chunk1" not in retrieval_service._chunks
        assert "chunk2" not in retrieval_service._chunks
        assert "chunk3" in retrieval_service._chunks
