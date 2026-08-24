"""
Week 4 Day 3: ChromaVectorStore 单元测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.ai.vector_store import ChromaVectorStore, VectorDocument


class TestChromaVectorStore:
    """ChromaVectorStore 单元测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # 清理
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture(scope="function")
    def vector_store(self, temp_dir):
        """创建向量存储实例"""
        import uuid
        # 使用唯一集合名避免冲突
        collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
        store = ChromaVectorStore(
            collection_name=collection_name,
            persist_directory=temp_dir,
        )

    @pytest.fixture
    def sample_documents(self):
        """示例文档"""
        return [
            VectorDocument(
                id="doc1",
                text="人工智能是计算机科学的一个分支",
                embedding=[0.1] * 384,  # ChromaDB 默认384维
                metadata={"source": "test", "category": "AI"},
            ),
            VectorDocument(
                id="doc2",
                text="机器学习是人工智能的子领域",
                embedding=[0.2] * 384,
                metadata={"source": "test", "category": "ML"},
            ),
            VectorDocument(
                id="doc3",
                text="深度学习是机器学习的一种方法",
                embedding=[0.3] * 384,
                metadata={"source": "test", "category": "DL"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_add_document(self, vector_store, sample_documents):
        """测试添加单个文档"""
        doc = sample_documents[0]
        doc_id = await vector_store.add_document(doc)
        
        assert doc_id == "doc1"
        
        # 验证文档已添加
        count = await vector_store.count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_add_documents_batch(self, vector_store, sample_documents):
        """测试批量添加文档"""
        ids = await vector_store.add_documents(sample_documents)
        
        assert len(ids) == 3
        assert set(ids) == {"doc1", "doc2", "doc3"}
        
        count = await vector_store.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_get_document(self, vector_store, sample_documents):
        """测试获取文档"""
        doc = sample_documents[0]
        await vector_store.add_document(doc)
        
        retrieved_doc = await vector_store.get_document("doc1")
        
        assert retrieved_doc is not None
        assert retrieved_doc.id == "doc1"
        assert retrieved_doc.text == doc.text
        assert retrieved_doc.metadata == doc.metadata

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, vector_store):
        """测试获取不存在的文档"""
        doc = await vector_store.get_document("nonexistent")
        assert doc is None

    @pytest.mark.asyncio
    async def test_search_similar_documents(self, vector_store, sample_documents):
        """测试向量相似度搜索"""
        # 添加文档
        await vector_store.add_documents(sample_documents)
        
        # 使用与 doc1 相似的查询向量
        query_embedding = [0.1] * 384
        
        results = await vector_store.search(query_embedding, limit=2)
        
        # 应该返回2个结果
        assert len(results) == 2
        
        # 第一个结果应该是 doc1 (最相似)
        assert results[0].document.id == "doc1"
        assert results[0].rank == 1
        
        # 相似度分数应该在合理范围内
        assert 0 <= results[0].score <= 1

    @pytest.mark.asyncio
    async def test_search_with_limit(self, vector_store, sample_documents):
        """测试限制搜索结果数量"""
        await vector_store.add_documents(sample_documents)
        
        query_embedding = [0.15] * 384
        
        # 只返回1个结果
        results = await vector_store.search(query_embedding, limit=1)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_delete_document(self, vector_store, sample_documents):
        """测试删除文档"""
        doc = sample_documents[0]
        await vector_store.add_document(doc)
        
        # 删除文档
        success = await vector_store.delete_document("doc1")
        assert success is True
        
        # 验证文档已删除
        count = await vector_store.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, vector_store):
        """测试删除不存在的文档"""
        success = await vector_store.delete_document("nonexistent")
        # Chroma 不会抛出错误，但返回 True
        assert success is True

    @pytest.mark.asyncio
    async def test_count_documents(self, vector_store, sample_documents):
        """测试文档计数"""
        # 初始为0
        count = await vector_store.count()
        assert count == 0
        
        # 添加2个文档
        await vector_store.add_documents(sample_documents[:2])
        count = await vector_store.count()
        assert count == 2
        
        # 再添加1个
        await vector_store.add_document(sample_documents[2])
        count = await vector_store.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_clear_collection(self, vector_store, sample_documents):
        """测试清空集合"""
        # 添加文档
        await vector_store.add_documents(sample_documents)
        assert await vector_store.count() == 3
        
        # 清空
        success = await vector_store.clear()
        assert success is True
        
        # 验证已清空
        count = await vector_store.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_search_empty_store(self, vector_store):
        """测试在空存储中搜索"""
        query_embedding = [0.1] * 384
        results = await vector_store.search(query_embedding, limit=10)
        
        # 应该返回空列表
        assert results == []

    @pytest.mark.asyncio
    async def test_document_metadata(self, vector_store):
        """测试文档元数据"""
        doc = VectorDocument(
            id="meta_doc",
            text="测试元数据",
            embedding=[0.5] * 384,
            metadata={
                "author": "test_user",
                "created_at": "2026-08-24",
                "tags": ["test", "metadata"],
            },
        )
        
        await vector_store.add_document(doc)
        
        # 获取文档并验证元数据
        retrieved = await vector_store.get_document("meta_doc")
        assert retrieved.metadata["author"] == "test_user"
        assert "tags" in retrieved.metadata
