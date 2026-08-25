"""
混合搜索系统
Week 4 Day 5 - RAG优化

功能：
1. BM25 关键词检索（词频统计）
2. 向量语义检索
3. 混合排名融合（Reciprocal Rank Fusion）
4. 提升检索召回率和准确性
"""

import math
from collections import Counter
from typing import List, Optional

import structlog

from src.ai.embeddings import EmbeddingProvider
from src.ai.vector_store import SearchResult, VectorDocument, VectorStore

logger = structlog.get_logger(__name__)


class BM25Retriever:
    """
    BM25 关键词检索器

    基于词频统计的关键词匹配算法，适合精确匹配场景
    特点：基于词项频率、文档长度归一化
    """

    def __init__(
        self,
        documents: List[VectorDocument],
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """
        初始化 BM25 检索器

        Args:
            documents: 文档列表
            k1: Term频率饱和参数（默认1.5）
            b: 文档长度归一化参数（默认0.75）
        """
        self.documents = documents
        self.k1 = k1
        self.b = b

        # 预处理文档
        self.doc_texts = [doc.text for doc in documents]
        self.tokenized_docs = [self._tokenize(text) for text in self.doc_texts]

        # 计算统计信息
        self.avg_doc_len = sum(len(doc) for doc in self.tokenized_docs) / max(len(self.tokenized_docs), 1)
        self.doc_freqs = self._compute_doc_frequencies()
        self.idf_scores = self._compute_idf()

        logger.info(
            "bm25_initialized",
            doc_count=len(documents),
            avg_doc_len=self.avg_doc_len,
            vocab_size=len(self.idf_scores),
        )

    def _tokenize(self, text: str) -> List[str]:
        """
        简单分词（空格分割 + 小写）

        Args:
            text: 输入文本

        Returns:
            分词列表
        """
        # 简单实现：空格分割 + 小写
        # 生产环境建议使用 jieba 或其他中文分词器
        return text.lower().split()

    def _compute_doc_frequencies(self) -> dict:
        """
        计算文档频率（DF：包含某词的文档数）

        Returns:
            {term: doc_count}
        """
        doc_freqs = {}

        for doc_tokens in self.tokenized_docs:
            unique_tokens = set(doc_tokens)
            for token in unique_tokens:
                doc_freqs[token] = doc_freqs.get(token, 0) + 1

        return doc_freqs

    def _compute_idf(self) -> dict:
        """
        计算 IDF（逆文档频率）

        IDF(q_i) = ln((N - n(q_i) + 0.5) / (n(q_i) + 0.5))

        Returns:
            {term: idf_score}
        """
        idf_scores = {}
        num_docs = len(self.documents)

        for term, df in self.doc_freqs.items():
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
            idf_scores[term] = idf

        return idf_scores

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        BM25 搜索

        BM25(D, Q) = Σ IDF(q_i) * (f(q_i, D) * (k1 + 1)) / (f(q_i, D) + k1 * (1 - b + b * |D| / avgdl))

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            搜索结果列表
        """
        query_tokens = self._tokenize(query)

        # 计算每个文档的BM25分数
        scores = []

        for idx, (doc, doc_tokens) in enumerate(zip(self.documents, self.tokenized_docs)):
            score = self._compute_bm25_score(query_tokens, doc_tokens)
            scores.append((idx, score))

        # 排序并取top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        top_results = scores[:top_k]

        # 构造SearchResult
        results = []
        for rank, (idx, score) in enumerate(top_results):
            result = SearchResult(
                document=self.documents[idx],
                score=score,
                rank=rank,
            )
            results.append(result)

        logger.info(
            "bm25_search_complete",
            query_length=len(query),
            results_count=len(results),
            top_score=results[0].score if results else 0.0,
        )

        return results

    def _compute_bm25_score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """
        计算单个文档的BM25分数

        Args:
            query_tokens: 查询分词
            doc_tokens: 文档分词

        Returns:
            BM25分数
        """
        score = 0.0
        doc_len = len(doc_tokens)
        term_freqs = Counter(doc_tokens)

        for q_term in query_tokens:
            if q_term not in self.idf_scores:
                continue

            idf = self.idf_scores[q_term]
            tf = term_freqs.get(q_term, 0)

            # BM25 公式
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)

            score += idf * (numerator / denominator)

        return score


class HybridRetriever:
    """
    混合检索器（BM25 + 向量）

    结合关键词匹配和语义检索，提升召回率和准确性
    使用 Reciprocal Rank Fusion（RRF）融合排名
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        rrf_k: int = 60,
    ):
        """
        初始化混合检索器

        Args:
            vector_store: 向量存储
            embedding_provider: 嵌入提供者
            bm25_weight: BM25权重（默认0.5）
            vector_weight: 向量权重（默认0.5）
            rrf_k: RRF常数（默认60）
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.rrf_k = rrf_k

        self.bm25_retriever: Optional[BM25Retriever] = None

        logger.info(
            "hybrid_retriever_initialized",
            bm25_weight=bm25_weight,
            vector_weight=vector_weight,
            rrf_k=rrf_k,
        )

    async def initialize_bm25(self, documents: List[VectorDocument]) -> None:
        """
        初始化 BM25 索引

        Args:
            documents: 文档列表
        """
        self.bm25_retriever = BM25Retriever(documents=documents)

        logger.info("bm25_index_initialized", doc_count=len(documents))

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> List[SearchResult]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_metadata: 元数据过滤

        Returns:
            融合后的搜索结果
        """
        # 向量检索
        query_embedding = await self.embedding_provider.embed_text(query)
        vector_results = await self.vector_store.search(
            query_embedding=query_embedding,
            limit=top_k * 2,  # 取2倍，便于融合
            filter_metadata=filter_metadata,
        )

        # BM25检索
        if self.bm25_retriever is None:
            # 如果BM25未初始化，使用向量检索结果初始化
            all_docs = [r.document for r in vector_results]
            await self.initialize_bm25(all_docs)

        bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)

        # 融合排名（RRF）
        fused_results = self.rank_fusion(
            bm25_results=bm25_results,
            vector_results=vector_results,
            top_k=top_k,
        )

        logger.info(
            "hybrid_search_complete",
            query_length=len(query),
            bm25_count=len(bm25_results),
            vector_count=len(vector_results),
            fused_count=len(fused_results),
        )

        return fused_results

    def rank_fusion(
        self,
        bm25_results: List[SearchResult],
        vector_results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion（互惠排名融合）

        RRF_score(d) = Σ 1 / (k + rank(d))

        Args:
            bm25_results: BM25检索结果
            vector_results: 向量检索结果
            top_k: 返回数量

        Returns:
            融合后的结果
        """
        # 构建文档得分字典
        doc_scores = {}

        # BM25贡献
        for rank, result in enumerate(bm25_results):
            doc_id = result.document.id
            rrf_score = self.bm25_weight / (self.rrf_k + rank + 1)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"document": result.document, "score": 0.0}

            doc_scores[doc_id]["score"] += rrf_score

        # 向量贡献
        for rank, result in enumerate(vector_results):
            doc_id = result.document.id
            rrf_score = self.vector_weight / (self.rrf_k + rank + 1)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"document": result.document, "score": 0.0}

            doc_scores[doc_id]["score"] += rrf_score

        # 排序
        sorted_items = sorted(doc_scores.items(), key=lambda x: x[1]["score"], reverse=True)

        # 构造结果
        fused_results = []
        for rank, (doc_id, data) in enumerate(sorted_items[:top_k]):
            result = SearchResult(
                document=data["document"],
                score=data["score"],
                rank=rank,
            )
            fused_results.append(result)

        return fused_results
