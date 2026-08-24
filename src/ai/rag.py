"""
RAG (检索增强生成) 系统
Week 4 Day 4 - RAG完整实现

功能：
1. 文档分块索引
2. 向量语义检索
3. 上下文增强生成
4. 知识库管理
5. 支持 ChromaDB/InMemory 向量存储
"""

from typing import List, Optional
from uuid import uuid4

import structlog

from src.ai.chunking import RecursiveCharacterTextSplitter, TextChunk
from src.ai.embeddings import EmbeddingProvider, create_embedding_provider
from src.ai.providers import BaseProvider, ProviderConfig, ProviderRequest, ProviderType
from src.ai.reranker import BaseReranker
from src.ai.vector_store import ChromaVectorStore, SearchResult, VectorDocument, VectorStore

logger = structlog.get_logger(__name__)


class RAGSystem:
    """
    RAG 系统

    将文档分块、向量检索与 LLM 生成结合，实现知识增强的回答

    特性：
    - 自动文档分块（RecursiveCharacterTextSplitter）
    - 灵活向量存储（ChromaDB / InMemory）
    - 独立 Embedding Provider
    - 流式/非流式生成
    """

    def __init__(
        self,
        llm_provider: BaseProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: Optional[VectorStore] = None,
        retrieval_top_k: int = 5,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        reranker: Optional[BaseReranker] = None,
    ):
        """
        初始化 RAG 系统

        Args:
            llm_provider: LLM 提供者（用于生成）
            embedding_provider: 嵌入提供者
            vector_store: 向量存储（默认使用 ChromaDB）
            retrieval_top_k: 检索结果数量
            chunk_size: 文档分块大小
            chunk_overlap: 分块重叠大小
            reranker: 重排序器（可选）
        """
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store or ChromaVectorStore(
            collection_name="rag_default", persist_directory="./data/chroma"
        )
        self.retrieval_top_k = retrieval_top_k
        self.reranker = reranker

        # 文档分块器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        logger.info(
            "rag_system_initialized",
            embedding_provider=type(embedding_provider).__name__,
            vector_store=type(self.vector_store).__name__,
            retrieval_top_k=retrieval_top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    async def add_document(
        self,
        text: str,
        metadata: Optional[dict] = None,
        document_id: Optional[str] = None,
        enable_chunking: bool = True,
    ) -> str:
        """
        添加文档到知识库（自动分块）

        Args:
            text: 文档文本
            metadata: 文档元数据
            document_id: 文档ID（可选）
            enable_chunking: 是否启用分块（默认True）

        Returns:
            文档ID（父文档）
        """
        doc_id = document_id or str(uuid4())

        # 分块
        if enable_chunking:
            chunks = self.text_splitter.split_text(text, metadata={"parent_doc_id": doc_id, **(metadata or {})})
        else:
            chunks = [TextChunk(text=text, metadata=metadata or {}, chunk_index=0, total_chunks=1)]

        # 为每个块生成嵌入并存储
        for chunk in chunks:
            embedding = await self.embedding_provider.embed_text(chunk.text)

            chunk_doc_id = f"{doc_id}_chunk_{chunk.chunk_index}"
            document = VectorDocument(
                id=chunk_doc_id,
                text=chunk.text,
                embedding=embedding,
                metadata=chunk.metadata,
            )

            await self.vector_store.add_document(document)

        logger.info(
            "document_indexed",
            document_id=doc_id,
            text_length=len(text),
            chunks_count=len(chunks),
        )

        return doc_id

    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
    ) -> List[str]:
        """
        批量添加文档

        Args:
            texts: 文档文本列表
            metadatas: 文档元数据列表

        Returns:
            文档ID列表
        """
        if metadatas is None:
            metadatas = [{}] * len(texts)

        if len(texts) != len(metadatas):
            raise ValueError("texts 和 metadatas 长度必须相同")

        document_ids = []

        for text, metadata in zip(texts, metadatas):
            doc_id = await self.add_document(text, metadata)
            document_ids.append(doc_id)

        logger.info("batch_documents_indexed", count=len(document_ids))

        return document_ids

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[dict] = None,
    ) -> List[SearchResult]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回数量（默认使用初始化时的配置）
            filter_metadata: 元数据过滤

        Returns:
            搜索结果列表
        """
        # 生成查询嵌入
        query_embedding = await self.embedding_provider.embed_text(query)

        # 向量搜索
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            limit=top_k or self.retrieval_top_k,
            filter_metadata=filter_metadata,
        )

        # 应用重排序
        if self.reranker:
            results = await self.reranker.rerank(query, results, top_k or self.retrieval_top_k)

        logger.info(
            "documents_retrieved",
            query_length=len(query),
            results_count=len(results),
            top_score=results[0].score if results else 0.0,
        )

        return results

    async def generate_with_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> tuple[str, List[SearchResult]]:
        """
        使用检索到的上下文生成回答

        Args:
            query: 用户查询
            top_k: 检索数量
            filter_metadata: 元数据过滤
            system_prompt: 系统提示词
            temperature: 温度参数

        Returns:
            (生成的回答, 检索到的文档)
        """
        # 检索相关文档
        results = await self.retrieve(query, top_k, filter_metadata)

        # 构造上下文
        context = self._build_context(results)

        # 构造增强提示词
        enhanced_prompt = self._build_prompt(query, context)

        # 构造请求并生成
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": enhanced_prompt})

        request = ProviderRequest(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=self.llm_provider.config.provider,
            model_id=self.llm_provider.config.metadata.get("default_model", "qwen2.5:7b"),
            messages=messages,
            temperature=temperature,
        )

        response = await self.llm_provider.complete(request)
        answer = response.content

        logger.info(
            "rag_generation_complete",
            query_length=len(query),
            context_length=len(context),
            answer_length=len(answer),
            sources_count=len(results),
        )

        return answer, results

    async def generate_with_context_stream(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        使用检索到的上下文生成回答（流式）

        Args:
            query: 用户查询
            top_k: 检索数量
            filter_metadata: 元数据过滤
            system_prompt: 系统提示词
            temperature: 温度参数

        Yields:
            (文本片段 or None, 检索结果)
            首次yield返回 (None, results)，之后返回 (text_chunk, None)
        """
        # 检索相关文档
        results = await self.retrieve(query, top_k, filter_metadata)

        # 首先返回检索结果
        yield None, results

        # 构造上下文和提示词
        context = self._build_context(results)
        enhanced_prompt = self._build_prompt(query, context)

        # 构造请求
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": enhanced_prompt})

        request = ProviderRequest(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=self.llm_provider.config.provider,
            model_id=self.llm_provider.config.metadata.get("default_model", "qwen2.5:7b"),
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        # 流式生成
        async for chunk in self.llm_provider.complete_stream(request):
            if chunk.content:
                yield chunk.content, None

        logger.info(
            "rag_stream_complete",
            query_length=len(query),
            sources_count=len(results),
        )

    def _build_context(self, results: List[SearchResult]) -> str:
        """
        构造上下文文本

        Args:
            results: 搜索结果

        Returns:
            格式化的上下文
        """
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            score_percent = int(result.score * 100)
            context_parts.append(f"[文档 {i}] (相关度: {score_percent}%)\n{result.document.text}")

        context = "\n\n".join(context_parts)
        return context

    def _build_prompt(self, query: str, context: str) -> str:
        """
        构造增强提示词

        Args:
            query: 用户查询
            context: 检索到的上下文

        Returns:
            增强提示词
        """
        if not context:
            return query

        prompt = f"""基于以下上下文信息回答问题。如果上下文中没有相关信息，请明确说明。

上下文信息：
{context}

问题：{query}

回答："""

        return prompt

    async def get_stats(self) -> dict:
        """
        获取 RAG 系统统计信息

        Returns:
            统计数据
        """
        doc_count = await self.vector_store.count()

        return {
            "total_documents": doc_count,
            "embedding_provider": type(self.embedding_provider).__name__,
            "retrieval_top_k": self.retrieval_top_k,
            "vector_store_type": type(self.vector_store).__name__,
        }

    async def clear_knowledge_base(self) -> bool:
        """
        清空知识库

        Returns:
            是否成功
        """
        success = await self.vector_store.clear()

        if success:
            logger.info("knowledge_base_cleared")

        return success
