"""Mock provider used by the existing SupplierRiskAgent fallback path."""

import json

from .base import RiskAssessmentProvider


class MockRiskAssessmentProvider(RiskAssessmentProvider):
    """Small deterministic mock provider used as the default adapter."""

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
