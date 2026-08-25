import os

os.environ.setdefault("SECRET_KEY", "1234567890abcdef1234567890abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "1234567890abcdef1234567890abcdef")

import asyncio

from src.ai.providers import (
    BaseProvider,
    ProviderConfig,
    ProviderRequest,
    ProviderResponse,
    ProviderStatus,
    ProviderType,
    TokenUsage,
)


class DummyProvider(BaseProvider):
    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            request_id=request.request_id,
            trace_id=request.trace_id,
            provider=request.provider,
            model_id=request.model_id,
            content="ok",
            usage=TokenUsage(input_tokens=5, output_tokens=3, total_tokens=8),
            finish_reason="stop",
            response_time_ms=0.0,
        )


async def _provider_smoke():
    provider = DummyProvider(
        ProviderConfig(
            provider=ProviderType.OLLAMA,
            api_key_name="ollama_api_key",
            base_url="http://localhost:11434",
            enabled=True,
        )
    )
    status = await provider.health_check()
    assert status == ProviderStatus.HEALTHY


def test_ai_provider_smoke():
    asyncio.run(_provider_smoke())
