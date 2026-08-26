"""Simple provider registry for the provider adapter scaffold."""

from typing import Dict, Type

from .base import RiskAssessmentProvider


_REGISTRY: Dict[str, Type[RiskAssessmentProvider]] = {}


def register_provider(name: str, provider_cls: Type[RiskAssessmentProvider]) -> None:
    """Register a provider class by a stable name."""
    _REGISTRY[name.lower()] = provider_cls


def get_provider(name: str = "mock") -> RiskAssessmentProvider:
    """Return an instantiated provider object, defaulting to the mock one.

    This is deliberately minimal and intentionally preserves the existing
    SupplierRiskAgent flow. The provider is just an optional adapter layer.
    """
    cls = _REGISTRY.get(name.lower())
    if cls is None:
        from .mock import MockRiskAssessmentProvider
        return MockRiskAssessmentProvider()
    return cls()


# Register the default provider used by tests and the existing path.
try:
    from .mock import MockRiskAssessmentProvider
except Exception:
    MockRiskAssessmentProvider = None

if MockRiskAssessmentProvider:
    register_provider("mock", MockRiskAssessmentProvider)
