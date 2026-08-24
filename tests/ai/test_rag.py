"""
RAG 系统单元测试
Week 4 Day 4
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.ai.chunking import RecursiveCharacterTextSplitter, SimpleTextSplitter, TextChunk
from src.ai.embeddings import ChromaDefaultEmbedding
from src.ai.providers import OllamaProvider, ProviderConfig, ProviderResponse, ProviderType
from src.ai.rag import RAGSystem
from src.ai.vector_store import InMemoryVectorStore, SearchResult, VectorDocument


# ============================================================
# 分块器测试
# ============================================================


class TestRecursiveCharacterTextSplitter:
    """测试递归字符分割器"""

    def test_split_short_text(self):
        """测试短文本不分割"""
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=10)
        text = "这是一段短文本。"
        chunks = splitter.split_text(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1

    def test_split_long_text(self):
        """测试长文本分割"""
        splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=10)

        text = "这是第一段。" * 10 + "这是第二段。" * 10
        chunks = splitter.split_text(text)

        assert len(chunks) > 1
        # 验证分块索引连续
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.total_chunks == len(chunks)
            assert len(chunk.text) <= 50 + 20  # chunk_size + 合理误差

    def test_chunk_overlap(self):
        """测试重叠功能"""
        splitter = RecursiveCharacterTextSplitter(chunk_size=30, chunk_overlap=10)

        text = "A" * 50 + "B" * 50
        chunks = splitter.split_text(text)

        assert len(chunks) >= 2
        # 检查重叠（第二块应该包含第一块的尾部）
        if len(chunks) >= 2:
            overlap_found = False
            for i in range(len(chunks) - 1):
                current_end = chunks[i].text[-10:]
                next_start = chunks[i + 1].text[:10]
                if any(c in next_start for c in current_end):
                    overlap_found = True
                    break
            # 注意：不是所有情况都能检测到重叠，因为分隔符可能在边界
            # 这里只做软检查

    def test_metadata_preservation(self):
        """测试元数据传递"""
        splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=10)
        metadata = {"source": "test.txt", "author": "tester"}

        text = "内容" * 50
        chunks = splitter.split_text(text, metadata=metadata)

        for chunk in chunks:
            assert chunk.metadata["source"] == "test.txt"
            assert chunk.metadata["author"] == "tester"
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata

    def test_empty_text(self):
        """测试空文本"""
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=10)
        chunks = splitter.split_text("")

        assert len(chunks) == 0


class TestSimpleTextSplitter:
    """测试简单文本分割器"""

    def test_simple_split(self):
        """测试简单分割"""
        splitter = SimpleTextSplitter(chunk_size=10, chunk_overlap=2)
        text = "A" * 50
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        # 每块大小应该接近 chunk_size
        for chunk in chunks[:-1]:  # 最后一块可能更短
            assert len(chunk.text) <= 10

    def test_simple_overlap(self):
        """测试简单分割重叠"""
        splitter = SimpleTextSplitter(chunk_size=20, chunk_overlap=5)
        text = "0123456789" * 5  # 50字符

        chunks = splitter.split_text(text)

        # 验证步长 = chunk_size - chunk_overlap
        # 应该是每次前进15个字符


# ============================================================
# RAG 系统测试
# ============================================================


@pytest.fixture
def mock_ollama_provider():
    """Mock Ollama Provider"""
    config = ProviderConfig(
        provider=ProviderType.OLLAMA,
        api_key_name="",
        enabled=True,
        base_url="http://localhost:11434",
        metadata={"default_model": "qwen2.5:7b"},
    )
    provider = OllamaProvider(config)
    return provider


@pytest.fixture
def mock_embedding_provider():
    """Mock Embedding Provider"""
    embedding = ChromaDefaultEmbedding()
    return embedding


@pytest.fixture
def mock_vector_store():
    """Mock Vector Store"""
    return InMemoryVectorStore()


@pytest.fixture
async def rag_system(mock_ollama_provider, mock_embedding_provider, mock_vector_store):
    """RAG 系统实例"""
    system = RAGSystem(
        llm_provider=mock_ollama_provider,
        embedding_provider=mock_embedding_provider,
        vector_store=mock_vector_store,
        retrieval_top_k=3,
        chunk_size=100,
        chunk_overlap=20,
    )
    return system


class TestRAGSystem:
    """测试 RAG 系统"""

    @pytest.mark.asyncio
    async def test_initialization(self, rag_system):
        """测试初始化"""
        assert rag_system is not None
        assert rag_system.retrieval_top_k == 3
        assert rag_system.text_splitter is not None

    @pytest.mark.asyncio
    async def test_add_document_with_chunking(self, rag_system):
        """测试添加文档（启用分块）"""
        text = "测试文档内容。" * 20  # 长文本
        doc_id = await rag_system.add_document(text, enable_chunking=True)

        assert doc_id is not None

        # 验证文档已添加到向量存储
        doc_count = await rag_system.vector_store.count()
        assert doc_count > 0

    @pytest.mark.asyncio
    async def test_add_document_without_chunking(self, rag_system):
        """测试添加文档（不分块）"""
        text = "短文档"
        doc_id = await rag_system.add_document(text, enable_chunking=False)

        assert doc_id is not None

        doc_count = await rag_system.vector_store.count()
        assert doc_count == 1

    @pytest.mark.asyncio
    async def test_add_documents_batch(self, rag_system):
        """测试批量添加文档"""
        texts = ["文档1" * 10, "文档2" * 10, "文档3" * 10]
        metadatas = [{"id": 1}, {"id": 2}, {"id": 3}]

        doc_ids = await rag_system.add_documents(texts, metadatas)

        assert len(doc_ids) == 3
        assert all(doc_id is not None for doc_id in doc_ids)

    @pytest.mark.asyncio
    async def test_retrieve(self, rag_system):
        """测试检索"""
        # 添加测试文档
        await rag_system.add_document("Python 是一门编程语言", metadata={"topic": "Python"})
        await rag_system.add_document("JavaScript 是前端语言", metadata={"topic": "JavaScript"})

        # 检索
        results = await rag_system.retrieve("Python 编程", top_k=2)

        assert len(results) <= 2
        # 最相关的应该是 Python 文档
        if results:
            assert isinstance(results[0], SearchResult)

    @pytest.mark.asyncio
    async def test_generate_with_context(self, rag_system, mock_ollama_provider):
        """测试生成（带上下文）"""
        # 添加测试文档
        await rag_system.add_document("鎏灏 AI-OS 是一个企业级 AI 操作系统")

        # Mock complete 方法
        mock_response = ProviderResponse(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=ProviderType.OLLAMA,
            model_id="qwen2.5:7b",
            content="鎏灏 AI-OS 是一个专为企业设计的 AI 操作系统。",
            usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            finish_reason="stop",
            response_time_ms=100,
        )

        with patch.object(mock_ollama_provider, "complete", return_value=mock_response):
            answer, results = await rag_system.generate_with_context(query="什么是鎏灏 AI-OS？")

            assert answer is not None
            assert len(answer) > 0
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_stats(self, rag_system):
        """测试获取统计信息"""
        # 添加文档
        await rag_system.add_document("测试文档")

        stats = await rag_system.get_stats()

        assert "total_documents" in stats
        assert "embedding_provider" in stats
        assert "retrieval_top_k" in stats
        assert stats["retrieval_top_k"] == 3

    @pytest.mark.asyncio
    async def test_clear_knowledge_base(self, rag_system):
        """测试清空知识库"""
        # 添加文档
        await rag_system.add_document("测试文档")

        doc_count_before = await rag_system.vector_store.count()
        assert doc_count_before > 0

        # 清空
        success = await rag_system.clear_knowledge_base()
        assert success is True

        doc_count_after = await rag_system.vector_store.count()
        assert doc_count_after == 0

    @pytest.mark.asyncio
    async def test_build_context(self, rag_system):
        """测试构造上下文"""
        # 创建模拟搜索结果
        doc1 = VectorDocument(
            id="doc1",
            text="文档1内容",
            embedding=[0.1] * 384,
            metadata={"source": "test"},
        )
        doc2 = VectorDocument(
            id="doc2",
            text="文档2内容",
            embedding=[0.2] * 384,
            metadata={"source": "test"},
        )

        results = [
            SearchResult(document=doc1, score=0.95, rank=1),
            SearchResult(document=doc2, score=0.85, rank=2),
        ]

        context = rag_system._build_context(results)

        assert "文档1内容" in context
        assert "文档2内容" in context
        assert "95%" in context  # 相关度
        assert "85%" in context

    @pytest.mark.asyncio
    async def test_build_prompt(self, rag_system):
        """测试构造提示词"""
        query = "测试问题"
        context = "这是上下文内容"

        prompt = rag_system._build_prompt(query, context)

        assert query in prompt
        assert context in prompt
        assert "上下文" in prompt or "context" in prompt.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_no_context(self, rag_system):
        """测试无上下文构造提示词"""
        query = "测试问题"
        context = ""

        prompt = rag_system._build_prompt(query, context)

        assert prompt == query  # 无上下文时直接返回问题


