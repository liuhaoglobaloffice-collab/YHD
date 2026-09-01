from src.ai.model_manager import ModelManager
from src.ai.providers import ModelConfig, ProviderGateway, ProviderType


def test_model_manager_switches_active_model():
    gateway = ProviderGateway()
    manager = ModelManager(gateway)

    gateway.register_model(
        ModelConfig(
            provider=ProviderType.OPENAI,
            model_id="gpt-4o-mini",
            model_name="GPT-4o mini",
            context_window=128000,
            enabled=True,
        )
    )
    gateway.register_model(
        ModelConfig(
            provider=ProviderType.OPENAI,
            model_id="gpt-4.1-mini",
            model_name="GPT-4.1 mini",
            context_window=128000,
            enabled=True,
        )
    )

    assert manager.get_active_model(ProviderType.OPENAI) == "gpt-4o-mini"
    switched = manager.switch_model(ProviderType.OPENAI, "gpt-4.1-mini")
    assert switched.model_id == "gpt-4.1-mini"
    assert manager.get_active_model(ProviderType.OPENAI) == "gpt-4.1-mini"
    provider_models = gateway.list_provider_models(ProviderType.OPENAI, enabled_only=True)
    assert {m.model_id for m in provider_models} == {"gpt-4o-mini", "gpt-4.1-mini"}


def test_model_manager_requires_registered_provider():
    manager = ModelManager(ProviderGateway())
    try:
        manager.switch_model(ProviderType.OLLAMA, "llama3.1")
        assert False, "Expected ResourceNotFoundError"
    except Exception as exc:  # pragma: no cover - contract check
        assert "Provider not registered" in str(exc)
