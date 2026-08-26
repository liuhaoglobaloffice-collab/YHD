import asyncio

from src.knowledge.embedding import EmbeddingService
from src.knowledge.rag_pipeline import RAGPipeline
from src.knowledge.vector_store import InMemoryVectorStore


def test_rag_pipeline_outputs_structured_result():
    store = InMemoryVectorStore()
    store.insert(
        document_id="doc-1",
        chunk_id="doc-1_chunk_0",
        content="LiuHao AI OS uses a supplier risk model with audit trails.",
        embedding=[0.2, 0.3, 0.4],
        metadata={"source": "supplier"},
    )

    pipeline = RAGPipeline(vector_store=store, provider_name="mock")
    result = asyncio.run(pipeline.query("supplier risk audit"))

    assert set(result.keys()) == {"query", "sources", "context", "answer", "metadata"}
    assert result["query"] == "supplier risk audit"
    assert isinstance(result["sources"], list)
    assert isinstance(result["context"], str)
    assert isinstance(result["answer"], str)
    assert isinstance(result["metadata"], dict)
    assert result["metadata"].get("provider") == "mock"


def test_retriever_uses_vector_search_and_ranking():
    store = InMemoryVectorStore()
    store.insert(
        document_id="doc-1",
        chunk_id="doc-1_chunk_0",
        content="Knowledge memory and supplier risk audit are linked.",
        embedding=[0.1, 0.2, 0.3],
        metadata={"source": "knowledge"},
    )

    from src.knowledge.retriever import Retriever
    retriever = Retriever(vector_store=store, provider_name="mock")
    hits = asyncio.run(retriever.search("supplier risk audit", limit=1))

    assert hits
    assert hits[0]["document_id"] == "doc-1"
    assert hits[0]["score"] >= 0.0
    assert hits[0]["content"]
