"""
RAG 重排序模块
Week 4 Day 5 - RAG 优化

功能：
1. 基于相似度重排序
2. LLM 重排序（使用 LLM 评估相关性）
3. 交叉编码器重排序（Cross-Encoder）
4. MMR（最大边际相关性）去重排序
"""

from typing import List, Optional

import structlog

from src.ai.vector_store import SearchResult

logger = structlog.get_logger(__name__)


class BaseReranker:
    """重排序器基类"""

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        重排序检索结果

        Args:
            query: 用户查询
            results: 原始检索结果
            top_k: 返回前K个结果

        Returns:
            重排序后的结果
        """
        raise NotImplementedError


class ScoreReranker(BaseReranker):
    """
    基于相似度分数重排序

    简单按照 score 降序排列
    """

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """按相似度分数重排序"""
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

        if top_k:
            sorted_results = sorted_results[:top_k]

        # 更新 rank
        for i, result in enumerate(sorted_results, 1):
            result.rank = i

        logger.info(
            "score_rerank_complete",
            query_length=len(query),
            input_count=len(results),
            output_count=len(sorted_results),
        )

        return sorted_results


class MMRReranker(BaseReranker):
    """
    最大边际相关性（MMR）重排序

    平衡相关性和多样性，避免返回过于相似的文档
    """

    def __init__(self, lambda_param: float = 0.5):
        """
        初始化 MMR 重排序器

        Args:
            lambda_param: 平衡参数（0-1）
                         1.0 = 完全相关性，0.0 = 完全多样性
        """
        self.lambda_param = lambda_param

        logger.info("mmr_reranker_initialized", lambda_param=lambda_param)

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """MMR 重排序"""
        if not results:
            return []

        if not top_k:
            top_k = len(results)

        # 已选择的结果
        selected = []
        # 候选结果池
        candidates = list(results)

        # 第一个选择相关性最高的
        first = max(candidates, key=lambda x: x.score)
        selected.append(first)
        candidates.remove(first)

        # 迭代选择剩余结果
        while len(selected) < top_k and candidates:
            best_candidate = None
            best_mmr_score = -float("inf")

            for candidate in candidates:
                # 计算与查询的相关性
                relevance = candidate.score

                # 计算与已选文档的最大相似度（使用embedding余弦相似度）
                max_similarity = 0.0
                if candidate.document.embedding and selected:
                    for selected_result in selected:
                        if selected_result.document.embedding:
                            sim = self._cosine_similarity(
                                candidate.document.embedding,
                                selected_result.document.embedding,
                            )
                            max_similarity = max(max_similarity, sim)

                # MMR 分数 = λ * 相关性 - (1-λ) * 最大相似度
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity

                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_candidate = candidate

            if best_candidate:
                selected.append(best_candidate)
                candidates.remove(best_candidate)

        # 更新 rank
        for i, result in enumerate(selected, 1):
            result.rank = i

        logger.info(
            "mmr_rerank_complete",
            query_length=len(query),
            input_count=len(results),
            output_count=len(selected),
            lambda_param=self.lambda_param,
        )

        return selected

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return dot_product / (norm1 * norm2)


class LLMReranker(BaseReranker):
    """
    LLM 重排序

    使用 LLM 评估每个文档与查询的相关性
    """

    def __init__(self, llm_provider, temperature: float = 0.1):
        """
        初始化 LLM 重排序器

        Args:
            llm_provider: LLM 提供者
            temperature: 温度参数（较低以获得稳定评分）
        """
        self.llm_provider = llm_provider
        self.temperature = temperature

        logger.info("llm_reranker_initialized", temperature=temperature)

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """LLM 重排序"""
        if not results:
            return []

        from uuid import uuid4

        from src.ai.providers import ProviderRequest

        # 为每个结果评分
        scored_results = []

        for result in results:
            # 构造评分提示词
            prompt = self._build_scoring_prompt(query, result.document.text)

            # 调用 LLM 评分
            request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=self.llm_provider.config.provider,
                model_id=self.llm_provider.config.metadata.get("default_model", "qwen2.5:7b"),
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=10,
            )

            try:
                response = await self.llm_provider.complete(request)
                # 解析分数（期望返回 0-10 的整数）
                score_text = response.content.strip()
                llm_score = self._parse_score(score_text)

                # 混合原始相似度和 LLM 评分
                combined_score = 0.5 * result.score + 0.5 * (llm_score / 10.0)

                scored_results.append((result, combined_score))

            except Exception as e:
                logger.warning(
                    "llm_rerank_failed_for_doc",
                    doc_id=result.document.id,
                    error=str(e),
                )
                # 失败时使用原始分数
                scored_results.append((result, result.score))

        # 按混合分数排序
        scored_results.sort(key=lambda x: x[1], reverse=True)

        if top_k:
            scored_results = scored_results[:top_k]

        # 更新结果和 rank
        reranked = []
        for i, (result, combined_score) in enumerate(scored_results, 1):
            result.score = combined_score
            result.rank = i
            reranked.append(result)

        logger.info(
            "llm_rerank_complete",
            query_length=len(query),
            input_count=len(results),
            output_count=len(reranked),
        )

        return reranked

    def _build_scoring_prompt(self, query: str, document: str) -> str:
        """构造评分提示词"""
        prompt = f"""请评估以下文档与查询的相关性。

查询：{query}

文档：{document}

请给出0-10的相关性评分（0=完全不相关，10=高度相关）。
只返回数字，不要解释。

评分："""
        return prompt

    def _parse_score(self, score_text: str) -> float:
        """解析 LLM 返回的分数"""
        # 尝试提取数字
        import re

        numbers = re.findall(r"\d+\.?\d*", score_text)
        if numbers:
            try:
                score = float(numbers[0])
                # 限制在 0-10 范围
                return max(0.0, min(10.0, score))
            except ValueError:
                pass

        # 解析失败，返回中等分数
        logger.warning("failed_to_parse_llm_score", score_text=score_text)
        return 5.0


def create_reranker(
    reranker_type: str = "score",
    llm_provider=None,
    lambda_param: float = 0.5,
    temperature: float = 0.1,
) -> BaseReranker:
    """
    创建重排序器

    Args:
        reranker_type: 重排序器类型（score, mmr, llm）
        llm_provider: LLM 提供者（llm类型必需）
        lambda_param: MMR 平衡参数
        temperature: LLM 温度参数

    Returns:
        重排序器实例
    """
    if reranker_type == "score":
        return ScoreReranker()
    elif reranker_type == "mmr":
        return MMRReranker(lambda_param=lambda_param)
    elif reranker_type == "llm":
        if not llm_provider:
            raise ValueError("LLMReranker requires llm_provider")
        return LLMReranker(llm_provider=llm_provider, temperature=temperature)
    else:
        raise ValueError(f"Unknown reranker type: {reranker_type}")
