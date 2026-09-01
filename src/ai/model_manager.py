"""Model manager for the Y1 runtime.

This is a small runtime layer that makes model registry and switching explicit,
so agents do not hard-code a single provider/model pair and can switch to a
verified available model when a provider or deployment changes.
"""

from typing import List, Optional

from .providers import ModelConfig, ProviderGateway, ProviderType


class ModelManager:
    """Domain-level model control plane used by Y1 runtime and UI.

    The manager intentionally keeps the interface simple: register, list, get
    active model, and switch active model. It does not replace the provider
    gateway; it wraps it with clearer runtime semantics.
    """

    def __init__(self, gateway: Optional[ProviderGateway] = None):
        self.gateway = gateway or ProviderGateway()

    def register_model(self, model: ModelConfig) -> ModelConfig:
        self.gateway.register_model(model)
        return model

    def list_models(self, provider: Optional[ProviderType] = None, enabled_only: bool = True) -> List[ModelConfig]:
        return self.gateway.list_models(provider=provider, enabled_only=enabled_only)

    def get_active_model(self, provider: ProviderType) -> Optional[str]:
        return self.gateway.get_active_model(provider)

    def switch_model(self, provider: ProviderType, model_id: str) -> ModelConfig:
        return self.gateway.switch_model(provider, model_id)
