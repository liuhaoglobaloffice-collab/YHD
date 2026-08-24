"""
查询扩展系统
Week 4 Day 5 - RAG优化

功能：
1. Multi-Query生成（使用LLM生成多个相关查询）
2. 查询改写
3. 提升检索召回率
"""

from uuid import uuid4

import structlog

from src.ai.providers import BaseProvider, ProviderRequest

logger = structlog.get_logger(__name__)


class QueryExpander:
    """
    查询扩展器

    使用LLM生成多个相关查询，提升检索召回率
    """

    def __init__(
        self,
        llm_provider: BaseProvider,
        num_queries: int = 3,
        temperature: float = 0.7,
    ):
        """
        初始化查询扩展器

        Args:
            llm_provider: LLM提供者
            num_queries: 生成查询数量（默认3）
            temperature: 温度参数（默认0.7）
        """
        self.llm_provider = llm_provider
        self.num_queries = num_queries
        self.temperature = temperature

        logger.info(
            "query_expander_initialized",
            num_queries=num_queries,
            temperature=temperature,
        )

    async def expand_query(self, original_query: str) -> list[str]:
        """
        扩展查询

        生成多个语义相关的查询变体

        Args:
            original_query: 原始查询

        Returns:
            扩展后的查询列表（包含原始查询）
        """
        prompt = f"""你是一个查询扩展助手。给定一个用户查询，生成{self.num_queries - 1}个语义相关的变体查询。

要求：
1. 保持原始语义
2. 使用不同表达方式
3. 每行一个查询
4. 不要编号或前缀
5. 不要解释

原始查询：
{original_query}

变体查询："""

        request = ProviderRequest(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=self.llm_provider.config.provider,
            model_id=self.llm_provider.config.metadata.get("default_model", "qwen2.5:7b"),
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )

        response = await self.llm_provider.complete(request)
        expanded_queries = self._parse_queries(response.content)

        # 加入原始查询
        all_queries = [original_query] + expanded_queries

        logger.info(
            "query_expanded",
            original_query=original_query,
            num_generated=len(expanded_queries),
            total_queries=len(all_queries),
        )

        return all_queries

    def _parse_queries(self, content: str) -> list[str]:
        """
        解析LLM生成的查询

        Args:
            content: LLM输出

        Returns:
            查询列表
        """
        lines = content.strip().split("\n")
        queries = []

        for line in lines:
            line = line.strip()

            # 跳过空行和标题行
            if not line or line.startswith("#") or line.lower().startswith("变体查询"):
                continue

            # 移除可能的前缀（如 "1. ", "- " 等）
            if line.startswith(("1.", "2.", "3.", "4.", "5.", "- ", "• ")):
                line = line.lstrip("12345.- •").strip()

            queries.append(line)

        return queries


async def expand_and_retrieve(
    query: str,
    retriever,
    expander: QueryExpander,
    top_k_per_query: int = 3,
    final_top_k: int = 5,
):
    """
    查询扩展 + 检索

    生成多个查询变体并检索，然后去重合并

    Args:
        query: 原始查询
        retriever: 检索器（必须有 search() 方法）
        expander: 查询扩展器
        top_k_per_query: 每个查询检索数量
        final_top_k: 最终返回数量

    Returns:
        检索结果列表
    """
    # 扩展查询
    expanded_queries = await expander.expand_query(query)

    # 对每个查询检索
    all_results = []
    seen_doc_ids = set()

    for exp_query in expanded_queries:
        results = await retriever.search(exp_query, top_k=top_k_per_query)

        for result in results:
            doc_id = result.document.id

            # 去重
            if doc_id not in seen_doc_ids:
                all_results.append(result)
                seen_doc_ids.add(doc_id)

    # 按分数排序并取top_k
    all_results.sort(key=lambda x: x.score, reverse=True)
    final_results = all_results[:final_top_k]

    logger.info(
        "expand_and_retrieve_complete",
        original_query=query,
        num_expanded_queries=len(expanded_queries),
        total_results=len(all_results),
        final_results=len(final_results),
    )

    return final_results
