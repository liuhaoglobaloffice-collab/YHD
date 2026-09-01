import os
from src.ai.providers import ProviderGateway, ModelConfig, ProviderType


def test_model_registry_persistence(tmp_path, monkeypatch):
    # Point the model registry persistence to a temporary directory
    monkeypatch.setenv("MODEL_REGISTRY_DIR", str(tmp_path))

    # Create a gateway and register a model
    gw = ProviderGateway()
    cfg = ModelConfig(
        provider=ProviderType.OLLAMA,
        model_id="local-test-1",
        model_name="local-test-1",
        context_window=32768,
        supports_streaming=True,
        supports_functions=True,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        enabled=True,
    )
    gw.register_model(cfg)

    # Active model should be the one registered
    active = gw.get_active_model(ProviderType.OLLAMA)
    assert active == "local-test-1"

    # Create a new gateway instance (simulating restart)
    gw2 = ProviderGateway()
    active2 = gw2.get_active_model(ProviderType.OLLAMA)
    assert active2 == "local-test-1"
