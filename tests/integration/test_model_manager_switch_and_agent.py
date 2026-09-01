import asyncio
from uuid import uuid4
from src.ai.providers import ProviderGateway, ModelConfig, ProviderType, MockProvider


def test_switch_model_affects_gateway(tmp_path, monkeypatch):
    # Use temporary directory for model registry persistence
    monkeypatch.setenv("MODEL_REGISTRY_DIR", str(tmp_path))

    gw = ProviderGateway()

    # Register a MockProvider instance so no external SDKs are required
    mock = MockProvider()
    gw.register_provider(mock)

    # Register two models for the same provider
    cfg1 = ModelConfig(provider=ProviderType.OPENAI, model_id="m1", model_name="m1", context_window=1024)
    cfg2 = ModelConfig(provider=ProviderType.OPENAI, model_id="m2", model_name="m2", context_window=1024)

    gw.register_model(cfg1)
    gw.register_model(cfg2)

    # Default active model should be set
    active = gw.get_active_model(ProviderType.OPENAI)
    assert active in ("m1", "m2")

    # Switch to m2 and verify persistence across gateway instance recreate
    gw.switch_model(ProviderType.OPENAI, "m2")
    assert gw.get_active_model(ProviderType.OPENAI) == "m2"

    # Simulate restart by creating a new gateway - it should load persisted active model
    gw2 = ProviderGateway()
    assert gw2.get_active_model(ProviderType.OPENAI) == "m2"

    # Ensure the gateway uses the active model when executing a completion
    # Register the same MockProvider instance in gw2 so execution is possible
    gw2.register_provider(MockProvider())

    resp = asyncio.run(
        gw2.complete(
            ProviderType.OPENAI,
            gw2.get_active_model(ProviderType.OPENAI),
            [{"role": "user", "content": "hello"}],
            trace_id=uuid4(),
        )
    )

    assert resp.model_id == "m2"
    assert "Mock Response" in resp.content
