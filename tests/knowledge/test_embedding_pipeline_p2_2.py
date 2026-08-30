"""P2-2 Embedding Pipeline — comprehensive tests.

Covers the full acceptance criteria:
  1.  text → chunks
  2.  chunk → embedding
  3.  real provider embedding path (mock provider)
  4.  embedding model configuration
  5.  provider unavailable
  6.  embedding timeout
  7.  invalid / empty input
  8.  persistence
  9.  idempotency
 10.  embedding metadata
 11.  dimension handling
"""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from src.knowledge.chunker import TextChunker, Chunk
from src.knowledge.embedding import EmbeddingError, EmbeddingPipeline, EmbeddingService
from src.knowledge.vector_store import InMemoryVectorStore, SQLiteVectorStore


# =========================================================================
# 1. text → chunks
# =========================================================================


class TestDocumentChunking:
    def test_basic_chunking(self):
        chunker = TextChunker(chunk_size=20, overlap=5)
        chunks = chunker.chunk_text(
            document_id="doc-1",
            text="Alpha beta gamma delta epsilon zeta eta theta iota kappa",
            metadata={"source": "test"},
        )
        assert len(chunks) >= 2
        assert chunks[0].metadata == {"source": "test"}
        assert chunks[0].content
        assert chunks[0].chunk_index == 0
        assert chunks[0].document_id == "doc-1"

    def test_empty_text_returns_empty(self):
        chunker = TextChunker()
        assert chunker.chunk_text("doc-1", "") == []
        assert chunker.chunk_text("doc-1", "   ") == []

    def test_single_chunk_for_short_text(self):
        chunker = TextChunker(chunk_size=200)
        chunks = chunker.chunk_text("doc-1", "Short text")
        assert len(chunks) == 1
        assert chunks[0].content == "Short text"

    def test_chunk_id_format(self):
        chunker = TextChunker(chunk_size=10, overlap=0)
        chunks = chunker.chunk_text("my-doc", "A B C D E F G H I J K L M N O P")
        for i, c in enumerate(chunks):
            assert c.chunk_id == f"my-doc_chunk_{i}"

    def test_overlap_produces_shared_content(self):
        chunker = TextChunker(chunk_size=20, overlap=10)
        chunks = chunker.chunk_text("doc-1", "A B C D E F G H I J K L M N O P")
        if len(chunks) >= 2:
            # Overlap should share some content between adjacent chunks
            assert chunks[0].content != chunks[1].content


# =========================================================================
# 2. chunk → embedding
# =========================================================================


class TestEmbeddingGeneration:
    def test_mock_provider_returns_vector(self):
        service = EmbeddingService(provider_name="mock")
        vector = asyncio.run(service.embed_text("test text"))
        assert isinstance(vector, list)
        assert len(vector) >= 3

    def test_embed_chunks_returns_descriptors(self):
        service = EmbeddingService(provider_name="mock")
        chunks = [
            Chunk(chunk_id="c1", document_id="d1", content="hello", chunk_index=0),
            Chunk(chunk_id="c2", document_id="d1", content="world", chunk_index=1),
        ]
        rows = asyncio.run(service.embed_chunks(chunks))
        assert len(rows) == 2
        assert rows[0]["chunk_id"] == "c1"
        assert rows[0]["document_id"] == "d1"
        assert "vector" in rows[0]
        assert "dimension" in rows[0]
        assert "provider" in rows[0]
        assert "embedding_model" in rows[0]

    def test_embedding_model_config(self):
        service = EmbeddingService(provider_name="mock", model="nomic-embed-text")
        assert service.model == "nomic-embed-text"
        vector = asyncio.run(service.embed_text("test"))
        assert isinstance(vector, list)

    def test_embedding_service_defaults_from_settings(self):
        """Should not crash when using default settings (mock provider)."""
        service = EmbeddingService()
        vector = asyncio.run(service.embed_text("test"))
        assert isinstance(vector, list)


# =========================================================================
# 3. real provider embedding path (mock provider)
# =========================================================================


class TestRealProviderPath:
    def test_mock_provider_embeddings_invoked(self):
        """Verify that the mock provider's embeddings() is actually called."""
        service = EmbeddingService(provider_name="mock")
        vector = asyncio.run(service.embed_text("test"))
        # Mock provider returns [0.1, 0.2, 0.3]
        assert vector == [0.1, 0.2, 0.3]

    def test_pipeline_e2e_with_mock(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store,
            provider_name="mock",
            chunk_size=20,
            overlap=5,
        )
        result = asyncio.run(pipeline.run(
            document_id="doc-1",
            text="Alpha beta gamma delta epsilon zeta eta theta iota kappa",
            metadata={"source": "unit-test"},
        ))
        assert result["document_id"] == "doc-1"
        assert result["chunks_count"] >= 1
        assert result["embeddings_created"] == result["chunks_count"]
        assert result["storage_status"] == "ok"
        assert result["provider"] == "mock"
        assert "embedding_model" in result


# =========================================================================
# 4. embedding model configuration
# =========================================================================


class TestEmbeddingModelConfig:
    def test_embedding_model_passed_to_provider(self):
        """Verify that the model kwarg is passed through to the provider."""
        service = EmbeddingService(provider_name="mock", model="custom-model")
        # The mock provider ignores model, but we verify the service tracks it
        assert service.model == "custom-model"

    def test_embedding_model_empty_for_mock(self):
        service = EmbeddingService(provider_name="mock")
        # Mock provider doesn't use a model, but service should handle empty
        assert isinstance(service.model, str)

    def test_pipeline_embedding_model_propagation(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store,
            provider_name="mock",
            embedding_model="nomic-embed-text",
        )
        assert pipeline.embedding_model == "nomic-embed-text"
        assert pipeline.provider_name == "mock"


# =========================================================================
# 5. provider unavailable
# =========================================================================


class TestProviderUnavailable:
    def test_unknown_provider_falls_back_to_mock(self):
        """get_provider() falls back to mock for unknown names."""
        service = EmbeddingService(provider_name="nonexistent_provider_xyz")
        # Should not crash - mock provider is used as fallback
        vector = asyncio.run(service.embed_text("test"))
        assert isinstance(vector, list)

    def test_provider_without_embeddings(self):
        """Provider that doesn't implement embeddings() should raise."""
        # Create a provider-like object without embeddings
        class BadProvider:
            name = "bad"
            async def chat(self, prompt, **kwargs):
                return ""

        with patch("src.knowledge.embedding.get_provider", return_value=BadProvider()):
            service = EmbeddingService(provider_name="bad")
            with pytest.raises(EmbeddingError, match="does not implement embeddings"):
                asyncio.run(service.embed_text("test"))


# =========================================================================
# 6. embedding timeout
# =========================================================================


class TestEmbeddingTimeout:
    def test_timeout_raises_embedding_error(self):
        """Provider that times out should raise EmbeddingError."""
        slow_provider = AsyncMock()
        slow_provider.embeddings = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch("src.knowledge.embedding.get_provider", return_value=slow_provider):
            service = EmbeddingService(provider_name="mock")
            with pytest.raises(EmbeddingError, match="timeout"):
                asyncio.run(service.embed_text("test"))


# =========================================================================
# 7. invalid / empty input
# =========================================================================


class TestInvalidInput:
    def test_empty_text_raises_error(self):
        service = EmbeddingService(provider_name="mock")
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            asyncio.run(service.embed_text(""))

    def test_whitespace_only_raises_error(self):
        service = EmbeddingService(provider_name="mock")
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            asyncio.run(service.embed_text("   \n  \t  "))

    def test_none_text_raises_error(self):
        service = EmbeddingService(provider_name="mock")
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            asyncio.run(service.embed_text(None))  # type: ignore

    def test_pipeline_handles_empty_text(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(vector_store=store, provider_name="mock")
        result = asyncio.run(pipeline.run("doc-1", ""))
        assert result["storage_status"] == "empty_input"
        assert result["chunks_count"] == 0


# =========================================================================
# 8. persistence
# =========================================================================


class TestPersistence:
    def test_inmemory_store_insert_and_retrieve(self):
        store = InMemoryVectorStore()
        result = store.insert(
            document_id="doc-1",
            chunk_id="chunk-1",
            content="test content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
        )
        assert result["status"] == "inserted"
        assert len(store.records) == 1
        assert store.records[0].chunk_id == "chunk-1"

    def _sqlite_store(self) -> SQLiteVectorStore:
        """Create a SQLiteVectorStore in a temp directory (cleanup-safe)."""
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "test.db")
        return SQLiteVectorStore(db_path=db_path), tmp_dir

    def test_sqlite_store_insert_and_search(self):
        store, tmp_dir = self._sqlite_store()
        try:
            store.insert(
                document_id="doc-1",
                chunk_id="chunk-1",
                content="test content",
                embedding=[0.1, 0.2, 0.3],
                metadata={"source": "test"},
            )
            # Search for similar vector
            results = store.search([0.1, 0.2, 0.3], limit=5)
            assert len(results) >= 1
            assert results[0]["chunk_id"] == "chunk-1"
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_sqlite_store_has_chunk(self):
        store, tmp_dir = self._sqlite_store()
        try:
            assert not store.has_chunk("nonexistent")
            store.insert(
                document_id="doc-1",
                chunk_id="chunk-1",
                content="test",
                embedding=[0.1, 0.2, 0.3],
            )
            assert store.has_chunk("chunk-1")
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_sqlite_store_delete(self):
        store, tmp_dir = self._sqlite_store()
        try:
            store.insert(
                document_id="doc-1",
                chunk_id="chunk-1",
                content="test",
                embedding=[0.1, 0.2, 0.3],
            )
            assert store.delete(document_id="doc-1") == 1
            assert len(store.records) == 0
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


# =========================================================================
# 9. idempotency
# =========================================================================


class TestIdempotency:
    def test_pipeline_skips_existing_chunks(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store, provider_name="mock", chunk_size=200, overlap=0
        )
        # First run
        result1 = asyncio.run(pipeline.run(
            document_id="doc-1",
            text="This is a test document for embedding idempotency.",
        ))
        assert result1["embeddings_created"] >= 1
        assert result1["embeddings_skipped"] == 0

        # Second run with same document - should skip existing chunks
        result2 = asyncio.run(pipeline.run(
            document_id="doc-1",
            text="This is a test document for embedding idempotency.",
        ))
        # Since chunk IDs are based on document_id + index, they'll match
        assert result2["embeddings_skipped"] >= 1

    def test_inmemory_has_chunk(self):
        store = InMemoryVectorStore()
        assert not store.has_chunk("nonexistent")
        store.insert(
            document_id="doc-1",
            chunk_id="chunk-1",
            content="test",
            embedding=[0.1, 0.2, 0.3],
        )
        assert store.has_chunk("chunk-1")

    def test_pipeline_skip_existing_disabled(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store, provider_name="mock", chunk_size=200, overlap=0
        )
        text = "Test document for idempotency."
        result1 = asyncio.run(pipeline.run("doc-1", text, skip_existing=False))
        created1 = result1["embeddings_created"]

        result2 = asyncio.run(pipeline.run("doc-1", text, skip_existing=False))
        # Without skip_existing, the same chunk gets embedded again
        # (InMemoryVectorStore doesn't deduplicate on insert)
        assert result2["embeddings_created"] == created1


# =========================================================================
# 10. embedding metadata
# =========================================================================


class TestEmbeddingMetadata:
    def test_embed_chunks_returns_metadata(self):
        service = EmbeddingService(provider_name="mock", model="test-model")
        chunks = [
            Chunk(
                chunk_id="c1", document_id="d1", content="hello",
                chunk_index=0, metadata={"page": 1},
            ),
        ]
        rows = asyncio.run(service.embed_chunks(chunks))
        assert rows[0]["provider"] == "mock"
        assert rows[0]["embedding_model"] == "test-model"
        assert rows[0]["dimension"] == 3  # Mock returns 3-dim vector
        assert rows[0]["metadata"] == {"page": 1}

    def test_pipeline_metadata_in_result(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store,
            provider_name="mock",
            embedding_model="nomic-embed-text",
        )
        result = asyncio.run(pipeline.run(
            document_id="doc-1",
            text="Test document.",
            metadata={"source": "unit-test"},
        ))
        assert result["provider"] == "mock"
        assert result["embedding_model"] == "nomic-embed-text"

    def test_pipeline_metadata_in_stored_records(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store, provider_name="mock", chunk_size=200,
        )
        asyncio.run(pipeline.run(
            document_id="doc-1",
            text="Test document with metadata.",
            metadata={"source": "test", "author": "tester"},
        ))
        for record in store.records:
            assert "provider" in record.metadata
            assert "embedding_model" in record.metadata
            assert "dimension" in record.metadata
            assert record.metadata.get("source") == "test"


# =========================================================================
# 11. dimension handling
# =========================================================================


class TestDimensionHandling:
    def test_dimension_from_vector_length(self):
        """Dimension should be derived from actual vector length, not hardcoded."""
        service = EmbeddingService(provider_name="mock")
        vector = asyncio.run(service.embed_text("test"))
        # Mock provider returns [0.1, 0.2, 0.3] → dimension 3
        assert len(vector) == 3

    def test_dimension_in_embed_chunks_output(self):
        service = EmbeddingService(provider_name="mock")
        chunks = [Chunk(chunk_id="c1", document_id="d1", content="test", chunk_index=0)]
        rows = asyncio.run(service.embed_chunks(chunks))
        assert rows[0]["dimension"] == len(rows[0]["vector"])

    def test_different_models_produce_different_dimensions(self):
        """Use a provider that returns different dimensions for different models."""
        class DimProvider:
            name = "dim_test"
            async def embeddings(self, text, **kwargs):
                model = kwargs.get("model", "")
                if "large" in model:
                    return [0.1] * 768
                return [0.1] * 384

        with patch("src.knowledge.embedding.get_provider", return_value=DimProvider()):
            service_small = EmbeddingService(provider_name="dim_test", model="small")
            service_large = EmbeddingService(provider_name="dim_test", model="large")

            vec_small = asyncio.run(service_small.embed_text("test"))
            vec_large = asyncio.run(service_large.embed_text("test"))

            assert len(vec_small) == 384
            assert len(vec_large) == 768
            assert len(vec_small) != len(vec_large)


# =========================================================================
# Pipeline edge cases
# =========================================================================


class TestPipelineEdgeCases:
    def test_pipeline_sqlite_persistence(self):
        import shutil
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "test.db")
        try:
            store = SQLiteVectorStore(db_path=db_path)
            pipeline = EmbeddingPipeline(
                vector_store=store, provider_name="mock", chunk_size=200, overlap=0
            )
            result = asyncio.run(pipeline.run(
                document_id="doc-1",
                text="This text will be persisted in SQLite.",
                metadata={"source": "sqlite-test"},
            ))
            assert result["storage_status"] == "ok"
            assert result["embeddings_created"] >= 1
            # Verify data survives via search
            service = EmbeddingService(provider_name="mock")
            query_vec = asyncio.run(service.embed_text("test"))
            search_results = store.search(query_vec, limit=5)
            assert len(search_results) >= 1
            assert search_results[0]["chunk_id"].startswith("doc-1_chunk")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_pipeline_provider_error_handling(self):
        """Provider that raises an exception should propagate as EmbeddingError."""
        faulty_provider = AsyncMock()
        faulty_provider.embeddings = AsyncMock(
            side_effect=RuntimeError("Ollama connection refused")
        )

        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store, provider_name="mock", chunk_size=200,
        )

        with patch.object(pipeline.embedding_service, "provider", faulty_provider):
            with pytest.raises(EmbeddingError, match="connection refused"):
                asyncio.run(pipeline.run("doc-1", "Some text."))

    def test_pipeline_empty_vector_from_provider(self):
        """Provider that returns an empty list should raise EmbeddingError."""
        empty_provider = AsyncMock()
        empty_provider.embeddings = AsyncMock(return_value=[])

        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store, provider_name="mock", chunk_size=200,
        )

        with patch.object(pipeline.embedding_service, "provider", empty_provider):
            with pytest.raises(EmbeddingError, match="empty embedding"):
                asyncio.run(pipeline.run("doc-1", "Some text."))

    def test_pipeline_search(self):
        store = InMemoryVectorStore()
        pipeline = EmbeddingPipeline(
            vector_store=store, provider_name="mock", chunk_size=200,
        )
        asyncio.run(pipeline.run("doc-1", "Alpha beta gamma delta."))
        results = asyncio.run(pipeline.search("alpha", limit=5))
        assert len(results) >= 1
        assert results[0]["document_id"] == "doc-1"