"""Regression tests for the ProviderGateway self-host fallback.

Built-in agents default to cloud provider types (MOONSHOT / OPENAI / ...).
On self-hosted deployments where only Ollama is configured, requests for
unregistered provider types must be remapped to an available REAL provider
and its default model instead of failing with "Provider not registered".

Security invariants:
- Requests for a registered REAL provider pass through unchanged.
- Fallback never remaps onto a MockProvider / production sentinel.
- When no real provider is available, the pair is returned unchanged so
  the gateway raises the original "not registered" error (fail closed).
"""

from src.ai.providers import (
    ModelConfig,
    MockProvider,
    ProviderConfig,
    ProviderGateway,
    ProviderType,
)


def _register_ollama(gateway: ProviderGateway, model: str = "qwen2.5:3b") -> None:
    gateway.register_provider(
        ProviderConfig(
            provider=ProviderType.OLLAMA,
            api_key_name="",
            base_url="http://localhost:11434",
            timeout_seconds=60,
            max_retries=3,
            enabled=True,
            metadata={"model": model},
        )
    )
    gateway.register_model(
        ModelConfig(
            provider=ProviderType.OLLAMA,
            model_id=model,
            model_name=model,
            context_window=32768,
            supports_streaming=True,
            supports_functions=False,
            input_cost_per_1k=0,
            output_cost_per_1k=0,
            enabled=True,
        )
    )


def test_unregistered_provider_remaps_to_ollama():
    gw = ProviderGateway()
    _register_ollama(gw)

    provider, model_id = gw._maybe_remap_provider(
        ProviderType.MOONSHOT, "moonshot-v1-8k"
    )

    assert provider == ProviderType.OLLAMA
    assert model_id == "qwen2.5:3b"


def test_registered_real_provider_passes_through_unchanged():
    gw = ProviderGateway()
    _register_ollama(gw)

    provider, model_id = gw._maybe_remap_provider(
        ProviderType.OLLAMA, "qwen2.5:3b"
    )

    assert provider == ProviderType.OLLAMA
    assert model_id == "qwen2.5:3b"


def test_mock_sentinel_is_remapped_when_real_provider_exists():
    """A MockProvider registered under the requested type (production
    sentinel / dev mock) must not serve the request when a real provider
    is available."""
    gw = ProviderGateway()
    _register_ollama(gw)
    # Simulate the production sentinel: a MockProvider posing as MOONSHOT
    sentinel = MockProvider()
    sentinel.provider_type = ProviderType.MOONSHOT
    gw.register_provider(sentinel)

    provider, model_id = gw._maybe_remap_provider(
        ProviderType.MOONSHOT, "moonshot-v1-8k"
    )

    assert provider == ProviderType.OLLAMA
    assert model_id == "qwen2.5:3b"


def test_no_real_provider_returns_unchanged_fail_closed():
    """With only a mock provider available, remap must NOT happen:
    the gateway keeps fail-closed behaviour."""
    gw = ProviderGateway()
    gw.register_provider(MockProvider())  # registers under OPENAI

    provider, model_id = gw._maybe_remap_provider(
        ProviderType.MOONSHOT, "moonshot-v1-8k"
    )

    assert provider == ProviderType.MOONSHOT
    assert model_id == "moonshot-v1-8k"
