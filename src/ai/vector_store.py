"""
向量存储抽象层
Week 4 Day 2 - Vector Store Integration

支持：
1. pgvector (PostgreSQL)
2. 内存向量存储（开发/测试）
3. 向量相似度搜索
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class VectorDocument:
    """向量文档"""

    id: str
    text: str
    embedding: List[float]
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SearchResult:
    """搜索结果"""

    document: VectorDocument
    score: float  # 相似度分数 (0-1)
    rank: int  # 排名


class VectorStore(ABC):
    """向量存储抽象基类"""

    @abstractmethod
    async def add_document(self, document: VectorDocument) -> str:
        """
        添加文档

        Args:
            document: 向量文档

        Returns:
            文档ID
        """
        pass

    @abstractmethod
    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        """
        批量添加文档

        Args:
            documents: 向量文档列表

        Returns:
            文档ID列表
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[SearchResult]:
        """
        向量相似度搜索

        Args:
            query_embedding: 查询向量
            limit: 返回数量
            filter_metadata: 元数据过滤

        Returns:
            搜索结果列表
        """
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """
        获取文档

        Args:
            document_id: 文档ID

        Returns:
            文档（如果存在）
        """
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """
        删除文档

        Args:
            document_id: 文档ID

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """
        获取文档总数

        Returns:
            文档数量
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """
        清空所有文档

        Returns:
            是否成功
        """
        pass


class InMemoryVectorStore(VectorStore):
    """
    内存向量存储

    用于开发和测试，不持久化
    """

    def __init__(self):
        self.documents: dict[str, VectorDocument] = {}
        logger.info("in_memory_vector_store_initialized")

    async def add_document(self, document: VectorDocument) -> str:
        """添加文档"""
        self.documents[document.id] = document
        logger.debug("document_added", document_id=document.id)
        return document.id

    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        """批量添加文档"""
        ids = []
        for doc in documents:
            doc_id = await self.add_document(doc)
            ids.append(doc_id)
        logger.info("documents_added", count=len(ids))
        return ids

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[SearchResult]:
        """
        向量相似度搜索（余弦相似度）

        Args:
            query_embedding: 查询向量
            limit: 返回数量
            filter_metadata: 元数据过滤

        Returns:
            搜索结果列表
        """
        results = []

        for doc in self.documents.values():
            # 元数据过滤
            if filter_metadata:
                if not all(doc.metadata.get(k) == v for k, v in filter_metadata.items()):
                    continue

            # 计算余弦相似度
            score = self._cosine_similarity(query_embedding, doc.embedding)
            results.append((doc, score))

        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)

        # 取前 limit 个
        top_results = results[:limit]

        # 构造搜索结果
        search_results = [
            SearchResult(document=doc, score=score, rank=i + 1)
            for i, (doc, score) in enumerate(top_results)
        ]

        logger.debug(
            "vector_search_complete",
            query_dim=len(query_embedding),
            total_docs=len(self.documents),
            results_count=len(search_results),
        )

        return search_results

    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """获取文档"""
        return self.documents.get(document_id)

    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        if document_id in self.documents:
            del self.documents[document_id]
            logger.debug("document_deleted", document_id=document_id)
            return True
        return False

    async def count(self) -> int:
        """获取文档总数"""
        return len(self.documents)

    async def clear(self) -> bool:
        """清空所有文档"""
        count = len(self.documents)
        self.documents.clear()
        logger.info("vector_store_cleared", documents_deleted=count)
        return True

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度 (0-1)
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"向量维度不匹配: {len(vec1)} vs {len(vec2)}")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity = dot_product / (magnitude1 * magnitude2)

        # 确保在 [0, 1] 范围内
        return max(0.0, min(1.0, (similarity + 1) / 2))


class ChromaVectorStore(VectorStore):
    """
    ChromaDB 向量存储实现
    
    特性:
    - 持久化存储
    - 内置嵌入功能
    - 高性能向量搜索
    - 自动索引管理
    """

    def __init__(
        self,
        collection_name: str = "liuhao_ai_os",
        persist_directory: str = "./data/chroma",
        embedding_function=None,
    ):
        """
        初始化 ChromaDB

        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录
            embedding_function: 嵌入函数 (可选)
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )

        # 创建 Chroma 客户端
        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
            )
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,  # None=使用默认嵌入
        )

        logger.info(
            "chroma_vector_store_initialized",
            collection=collection_name,
            persist_dir=persist_directory,
        )

    async def add_document(self, document: VectorDocument) -> str:
        """添加文档到 Chroma"""
        self.collection.add(
            ids=[document.id],
            embeddings=[document.embedding],
            documents=[document.text],
            metadatas=[document.metadata or {}],
        )

        logger.debug("document_added_to_chroma", document_id=document.id)
        return document.id

    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        """批量添加文档"""
        if not documents:
            return []

        ids = [doc.id for doc in documents]
        embeddings = [doc.embedding for doc in documents]
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata or {} for doc in documents]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        logger.info(
            "documents_added_to_chroma",
            count=len(documents),
        )
        return ids

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[SearchResult]:
        """向量相似度搜索"""
        # Chroma 搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=filter_metadata,  # 元数据过滤
        )

        # 构造搜索结果
        search_results = []
        
        if results["ids"] and len(results["ids"]) > 0:
            ids = results["ids"][0]
            documents_text = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for i, (doc_id, text, metadata, distance) in enumerate(
                zip(ids, documents_text, metadatas, distances)
            ):
                # Chroma 返回距离，需要转换为相似度
                # 距离越小，相似度越高
                # 使用简单的转换: similarity = 1 / (1 + distance)
                score = 1.0 / (1.0 + distance)
                
                doc = VectorDocument(
                    id=doc_id,
                    text=text,
                    embedding=[],  # Chroma 不返回原始向量
                    metadata=metadata,
                )
                
                search_results.append(
                    SearchResult(document=doc, score=score, rank=i + 1)
                )

        logger.debug(
            "chroma_search_complete",
            results_count=len(search_results),
        )

        return search_results

    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """获取文档"""
        results = self.collection.get(
            ids=[document_id],
            include=["documents", "metadatas", "embeddings"],
        )

        if results["ids"]:
            return VectorDocument(
                id=results["ids"][0],
                text=results["documents"][0],
                embedding=results["embeddings"][0] if results["embeddings"] else [],
                metadata=results["metadatas"][0] if results["metadatas"] else {},
            )
        return None

    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            self.collection.delete(ids=[document_id])
            logger.debug("document_deleted_from_chroma", document_id=document_id)
            return True
        except Exception as e:
            logger.warning("document_delete_failed", document_id=document_id, error=str(e))
            return False

    async def count(self) -> int:
        """获取文档总数"""
        return self.collection.count()

    async def clear(self) -> bool:
        """清空所有文档"""
        try:
            count = await self.count()
            # Chroma 没有直接的 clear 方法，需要删除并重新创建集合
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.create_collection(self.collection.name)
            logger.info("chroma_collection_cleared", documents_deleted=count)
            return True
        except Exception as e:
            logger.error("chroma_clear_failed", error=str(e))
            return False
