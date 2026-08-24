"""
测试 Reranker 模块
Week 4 Day 5 - RAG优化测试
"""

import pytest

from src.ai.providers import BaseProvider, ProviderConfig, ProviderResponse, ProviderType
from src.ai.reranker import (
    BaseReranker,
    LLMReranker,
    MMRReranker,
    ScoreReranker,
    create_reranker,
)
from src.ai.vector_store import SearchResult, VectorDocument


class MockProvider(BaseProvider):
    """Mock LLM Provider for testing"""

    def __init__(self):
        config = ProviderConfig(
            provider=ProviderType.OLLAMA,  # Use existing type
            api_key_name="mock_key",
            base_url="http://localhost",
        )
        super().__init__(config)
        self.mock_scores = [8, 6, 9, 5, 7]  # Predefined scores

    async def complete(self, request) -> ProviderResponse:
        # Return mock score as content
        score_idx = len(self.mock_scores) - 1
        score = self.mock_scores[score_idx % len(self.mock_scores)]
        return ProviderResponse(
            request_id=request.request_id,
            provider=ProviderType.MOCK,
            model_id="mock-model",
            content=str(score),
            completion_tokens=1,
            prompt_tokens=1,
            total_tokens=2,
        )

    async def complete_stream(self, request):
        yield ProviderResponse(
            request_id=request.request_id,
            provider=ProviderType.MOCK,
            model_id="mock-model",
            content="7",
            completion_tokens=1,
            prompt_tokens=1,
            total_tokens=2,
        )

    async def embed(self, request):
        return [0.1, 0.2, 0.3]


@pytest.fixture
def sample_results():
    """创建示例搜索结果"""
    results = []
    docs = [
        ("Python是一种编程语言", 0.9),
        ("Java也是编程语言", 0.85),
        ("机器学习很有趣", 0.8),
        ("深度学习是AI的分支", 0.75),
        ("自然语言处理是NLP", 0.7),
    ]

    for i, (text, score) in enumerate(docs):
        doc = VectorDocument(
            id=f"doc_{i}",
            text=text,
            embedding=[0.1 * i] * 5,
            metadata={"index": i},
        )
        results.append(SearchResult(document=doc, score=score, rank=i))

    return results


@pytest.mark.asyncio
class TestScoreReranker:
    """测试基于分数的重排序器"""

    async def test_basic_reranking(self, sample_results):
        """测试基本重排序"""
        reranker = ScoreReranker()
        reranked = await reranker.rerank("query", sample_results, top_k=3)

        assert len(reranked) == 3
        assert reranked[0].score >= reranked[1].score >= reranked[2].score

    async def test_top_k_limit(self, sample_results):
        """测试top_k限制"""
        reranker = ScoreReranker()
        reranked = await reranker.rerank("query", sample_results, top_k=2)

        assert len(reranked) == 2
        assert reranked[0].score == 0.9
        assert reranked[1].score == 0.85

    async def test_empty_results(self):
        """测试空结果"""
        reranker = ScoreReranker()
        reranked = await reranker.rerank("query", [], top_k=5)

        assert len(reranked) == 0


@pytest.mark.asyncio
class TestMMRReranker:
    """测试最大边际相关性重排序器"""

    async def test_diversity_balancing(self, sample_results):
        """测试多样性平衡"""
        # lambda=1.0: 纯相关性（应该与 ScoreReranker 一致）
        reranker_rel = MMRReranker(lambda_param=1.0)
        reranked_rel = await reranker_rel.rerank("query", sample_results, top_k=3)

        # lambda=0.0: 纯多样性（应该选择差异最大的）
        reranker_div = MMRReranker(lambda_param=0.0)
        reranked_div = await reranker_div.rerank("query", sample_results, top_k=3)

        assert len(reranked_rel) == 3
        assert len(reranked_div) == 3

        # 纯相关性时，第一个结果应该是最高分
        assert reranked_rel[0].score == 0.9

    async def test_mmr_iteration(self, sample_results):
        """测试MMR迭代过程"""
        reranker = MMRReranker(lambda_param=0.7)
        reranked = await reranker.rerank("query", sample_results, top_k=5)

        assert len(reranked) == 5
        # 第一个结果应该是最高分（初始化）
        assert reranked[0].score == 0.9

    async def test_empty_results(self):
        """测试空结果"""
        reranker = MMRReranker()
        reranked = await reranker.rerank("query", [], top_k=5)

        assert len(reranked) == 0


@pytest.mark.asyncio
class TestLLMReranker:
    """测试LLM重排序器"""

    async def test_llm_scoring(self, sample_results):
        """测试LLM评分"""
        mock_provider = MockProvider()
        reranker = LLMReranker(llm_provider=mock_provider)

        reranked = await reranker.rerank("Python编程", sample_results, top_k=3)

        assert len(reranked) == 3
        # 所有结果应该有新的分数
        for result in reranked:
            assert 0 <= result.score <= 1.0

    async def test_score_parsing(self, sample_results):
        """测试分数解析"""
        mock_provider = MockProvider()
        reranker = LLMReranker(llm_provider=mock_provider)

        # Mock provider返回固定分数
        reranked = await reranker.rerank("query", sample_results[:2], top_k=2)

        assert len(reranked) == 2
        # 分数应该被归一化到[0,1]
        assert all(0 <= r.score <= 1.0 for r in reranked)

    async def test_empty_results(self):
        """测试空结果"""
        mock_provider = MockProvider()
        reranker = LLMReranker(llm_provider=mock_provider)

        reranked = await reranker.rerank("query", [], top_k=5)

        assert len(reranked) == 0


def test_create_reranker_score():
    """测试工厂方法：ScoreReranker"""
    reranker = create_reranker(reranker_type="score")

    assert isinstance(reranker, ScoreReranker)


def test_create_reranker_mmr():
    """测试工厂方法：MMRReranker"""
    reranker = create_reranker(reranker_type="mmr", lambda_param=0.8)

    assert isinstance(reranker, MMRReranker)
    assert reranker.lambda_param == 0.8


def test_create_reranker_llm():
    """测试工厂方法：LLMReranker"""
    mock_provider = MockProvider()
    reranker = create_reranker(reranker_type="llm", llm_provider=mock_provider)

    assert isinstance(reranker, LLMReranker)
    assert reranker.llm_provider is mock_provider


def test_create_reranker_invalid_type():
    """测试工厂方法：无效类型"""
    with pytest.raises(ValueError, match="Unknown reranker type"):
        create_reranker(reranker_type="invalid")


def test_create_reranker_llm_missing_provider():
    """测试工厂方法：LLM类型但未提供provider"""
    with pytest.raises(ValueError, match="LLMReranker requires llm_provider"):
        create_reranker(reranker_type="llm")
