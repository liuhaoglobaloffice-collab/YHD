import asyncio
import json

from src.providers.registry import get_provider, register_provider
from src.providers.base import RiskAssessmentProvider


class DemoProvider(RiskAssessmentProvider):
    name = "demo"

    async def analyze(self, prompt: str) -> str:
        return json.dumps({
            "risk_level": "LOW",
            "overall_score": 30.0,
            "recommendations": ["monitor"],
        })


def test_provider_registry_and_mock_provider_contract():
    async def _run():
        provider = get_provider("mock")
        payload = await provider.analyze("prompt")
        parsed = json.loads(payload)
        assert parsed["risk_level"] == "MEDIUM"
        assert parsed["overall_score"] == 80.0

        register_provider("demo", DemoProvider)
        adapter = get_provider("demo")
        payload2 = await adapter.analyze("prompt")
        parsed2 = json.loads(payload2)
        assert parsed2["risk_level"] == "LOW"
        assert parsed2["recommendations"] == ["monitor"]

    asyncio.run(_run())
