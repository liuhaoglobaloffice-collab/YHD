"""
测试混合搜索模块
Week 4 Day 5 - RAG优化测试
"""

import pytest

from src.ai.embeddings import EmbeddingProvider
from src.ai.hybrid_search import BM25Retriever, HybridRetriever
from src.ai.vector_store import SearchResult, VectorDocument, VectorStore


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock Embedding Provider for testing"""

    async def embed_text(self, text: str) -> list[float]:
        # Simple hash-based mock embedding
        return [float(ord(c)) / 100 for c in text[:10].ljust(10)]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(text) for text in texts]

    def get_dimension(self) -> int:
        return 10


class MockVectorStore(VectorStore):
    """Mock Vector Store for testing"""

    def __init__(self):
        self.documents = []

    async def add_document(self, document: VectorDocument) -> str:
        self.documents.append(document)
        return document.id

    async def add_documents(self, documents: list[VectorDocument]) -> list[str]:
        for doc in documents:
            await self.add_document(doc)
        return [doc.id for doc in documents]

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[SearchResult]:
        # Simple cosine similarity mock
        results = []
        for i, doc in enumerate(self.documents):
            # Mock similarity based on embedding dot product
            score = sum(a * b for a, b in zip(query_embedding, doc.embedding))
            results.append(SearchResult(document=doc, score=score, rank=i))

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def delete_document(self, document_id: str) -> bool:
        self.documents = [doc for doc in self.documents if doc.id != document_id]
        return True

    async def count(self) -> int:
        return len(self.documents)

    async def get_document(self, document_id: str) -> VectorDocument | None:
        for doc in self.documents:
            if doc.id == document_id:
                return doc
        return None

    async def clear(self) -> bool:
        self.documents = []
        return True


@pytest.fixture
def sample_documents():
    """创建示例文档"""
    docs = [
        VectorDocument(
            id="doc_1",
            text="Python is a programming language",
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            metadata={"category": "tech"},
        ),
        VectorDocument(
            id="doc_2",
            text="Machine learning is part of AI",
            embedding=[0.2, 0.3, 0.4, 0.5, 0.6],
            metadata={"category": "ai"},
        ),
        VectorDocument(
            id="doc_3",
            text="Python programming tutorial",
            embedding=[0.1, 0.25, 0.35, 0.4, 0.5],
            metadata={"category": "tech"},
        ),
        VectorDocument(
            id="doc_4",
            text="Deep learning neural networks",
            embedding=[0.3, 0.4, 0.5, 0.6, 0.7],
            metadata={"category": "ai"},
        ),
        VectorDocument(
            id="doc_5",
            text="Natural language processing NLP",
            embedding=[0.25, 0.35, 0.45, 0.55, 0.65],
            metadata={"category": "ai"},
        ),
    ]
    return docs


class TestBM25Retriever:
    """测试BM25检索器"""

    def test_initialization(self, sample_documents):
        """测试初始化"""
        retriever = BM25Retriever(documents=sample_documents)

        assert retriever.documents == sample_documents
        assert len(retriever.tokenized_docs) == 5
        assert retriever.avg_doc_len > 0
        assert len(retriever.idf_scores) > 0

    def test_tokenize(self, sample_documents):
        """测试分词"""
        retriever = BM25Retriever(documents=sample_documents)

        tokens = retriever._tokenize("Python Programming")
        assert tokens == ["python", "programming"]

    def test_doc_frequencies(self, sample_documents):
        """测试文档频率计算"""
        retriever = BM25Retriever(documents=sample_documents)

        # "python" appears in 2 documents
        assert retriever.doc_freqs.get("python", 0) == 2
        # "learning" appears in 2 documents
        assert retriever.doc_freqs.get("learning", 0) == 2

    def test_idf_scores(self, sample_documents):
        """测试IDF分数"""
        retriever = BM25Retriever(documents=sample_documents)

        # Common words should have lower IDF
        # Rare words should have higher IDF
        assert "python" in retriever.idf_scores
        assert retriever.idf_scores["python"] > 0

    def test_search(self, sample_documents):
        """测试BM25搜索"""
        retriever = BM25Retriever(documents=sample_documents)

        results = retriever.search("Python programming", top_k=2)

        assert len(results) == 2
        assert results[0].score >= results[1].score
        # "Python" should match doc_1 or doc_3
        assert results[0].document.id in ["doc_1", "doc_3"]

    def test_empty_query(self, sample_documents):
        """测试空查询"""
        retriever = BM25Retriever(documents=sample_documents)

        results = retriever.search("", top_k=3)

        assert len(results) == 3
        # Empty query should return documents with score 0
        assert all(r.score == 0.0 for r in results)


@pytest.mark.asyncio
class TestHybridRetriever:
    """测试混合检索器"""

    async def test_initialization(self):
        """测试初始化"""
        vector_store = MockVectorStore()
        embedding_provider = MockEmbeddingProvider()

        retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            bm25_weight=0.5,
            vector_weight=0.5,
        )

        assert retriever.vector_store is vector_store
        assert retriever.embedding_provider is embedding_provider
        assert retriever.bm25_weight == 0.5
        assert retriever.vector_weight == 0.5

    async def test_initialize_bm25(self, sample_documents):
        """测试BM25初始化"""
        vector_store = MockVectorStore()
        embedding_provider = MockEmbeddingProvider()

        retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )

        await retriever.initialize_bm25(sample_documents)

        assert retriever.bm25_retriever is not None
        assert len(retriever.bm25_retriever.documents) == 5

    async def test_hybrid_search(self, sample_documents):
        """测试混合搜索"""
        vector_store = MockVectorStore()
        embedding_provider = MockEmbeddingProvider()

        # Add documents to vector store
        await vector_store.add_documents(sample_documents)

        retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )

        # Initialize BM25
        await retriever.initialize_bm25(sample_documents)

        # Search
        results = await retriever.search("Python programming", top_k=3)

        assert len(results) == 3
        assert results[0].score >= results[1].score >= results[2].score

    async def test_rank_fusion(self, sample_documents):
        """测试RRF排名融合"""
        vector_store = MockVectorStore()
        embedding_provider = MockEmbeddingProvider()

        retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
        )

        # Create mock results
        bm25_results = [
            SearchResult(document=sample_documents[0], score=10.0, rank=0),
            SearchResult(document=sample_documents[1], score=8.0, rank=1),
        ]

        vector_results = [
            SearchResult(document=sample_documents[1], score=0.9, rank=0),
            SearchResult(document=sample_documents[2], score=0.8, rank=1),
        ]

        # Fuse
        fused = retriever.rank_fusion(bm25_results, vector_results, top_k=3)

        assert len(fused) == 3
        # doc_1 should have high score (from both BM25 and vector)
        assert fused[0].document.id == "doc_2"  # doc_1 appears in both lists
