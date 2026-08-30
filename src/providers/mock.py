"""Mock provider used by the existing SupplierRiskAgent fallback path.

Phase 2.1 extends this module with a lightweight LLMProvider-compatible mock
implementation so the root registry can expose the same interface shape for
mock, OpenAI, and self-host providers.
"""

import json
from typing import Any, List

from .base import RiskAssessmentProvider
from .llm_base import LLMProvider


class MockRiskAssessmentProvider(RiskAssessmentProvider, LLMProvider):
    """Small deterministic mock provider used as the default adapter.

    Phase 2.1 broadens this class with the minimal LLM methods required by the
    new unified interface while keeping the original `analyze()` contract
    intact for the existing Supplier Risk flow.
    """

    name = "mock"

    async def analyze(self, prompt: str) -> str:
        return json.dumps({
            "compliance_score": 75.0,
            "financial_score": 80.0,
            "delivery_score": 70.0,
            "quality_score": 85.0,
            "communication_score": 90.0,
            "overall_score": 80.0,
            "risk_level": "MEDIUM",
            "strengths": ["高品质产品", "响应迅速"],
            "weaknesses": ["价格偏高"],
            "opportunities": ["市场扩张机会"],
            "threats": ["市场竞争激烈"],
        }, ensure_ascii=False)

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        return f"[mock] reply for: {prompt}"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[mock] generated text for: {prompt}"

    async def embeddings(self, text: str, **kwargs: Any) -> List[float]:
        return [0.1, 0.2, 0.3]

    async def health_check(self, timeout: float = 10.0) -> dict:
        """Mock provider is always available (no external dependency).

        Returns
        -------
        dict
            ``{"provider": "mock", "status": "healthy", "detail": ...}``
        """
        return {
            "provider": "mock",
            "status": "healthy",
            "detail": "mock provider is always available (no real LLM)",
        }
