import asyncio

from src.knowledge.chunker import TextChunker
from src.knowledge.embedding import EmbeddingPipeline, EmbeddingService
from src.knowledge.vector_store import InMemoryVectorStore


def test_document_chunking():
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


def test_embedding_generation():
    service = EmbeddingService(provider_name="mock")
    vector = asyncio.run(service.embed_text("phase2.2 embedding test"))
    assert isinstance(vector, list)
    assert len(vector) >= 3


def test_vector_store_insert_search():
    store = InMemoryVectorStore()
    store.insert(
        document_id="doc-1",
        chunk_id="doc-1_chunk_0",
        content="This is a test chunk.",
        embedding=[0.1, 0.2, 0.3],
        metadata={"source": "test"},
    )
    results = store.search([0.1, 0.2, 0.3], limit=5)
    assert results
    assert results[0]["chunk_id"] == "doc-1_chunk_0"
    assert results[0]["document_id"] == "doc-1"


def test_embedding_pipeline_e2e():
    store = InMemoryVectorStore()
    pipeline = EmbeddingPipeline(vector_store=store, provider_name="mock", chunk_size=20, overlap=5)
    payload = asyncio.run(pipeline.run(
        document_id="doc-1",
        text="Alpha beta gamma delta epsilon zeta eta theta iota kappa",
        metadata={"source": "unit-test"},
    ))
    assert payload["document_id"] == "doc-1"
    assert payload["chunks_count"] >= 1
    assert payload["embeddings_created"] == payload["chunks_count"]
    assert payload["storage_status"] == "ok"

    query = asyncio.run(pipeline.search("alpha beta", limit=5))
    assert query
    assert query[0]["document_id"] == "doc-1"
