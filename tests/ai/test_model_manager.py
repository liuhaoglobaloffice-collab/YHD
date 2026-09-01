from unittest.mock import MagicMock

import os
import tempfile
import pytest

# Isolate model registry persistence for tests
os.environ.setdefault("MODEL_REGISTRY_DIR", tempfile.mkdtemp())

from src.ai.model_manager import ModelManager
from src.ai.providers import ModelConfig, ProviderGateway, ProviderType
from src.api.factories.workforce import get_workforce_service
from src.identity.audit import AuditService


@pytest.mark.asyncio
async def test_workforce_factory_uses_runtime_audit_instance():
    service = await get_workforce_service(MagicMock())
    assert isinstance(service.audit, AuditService)


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
        # Allow either provider-not-registered or model-not-found messages (both indicate missing registration)
        assert ("Provider not registered" in str(exc)) or ("Model not found" in str(exc))
