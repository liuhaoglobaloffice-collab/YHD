"""Simple provider registry for the provider adapter scaffold.

Phase 2.1 updates the registry to support a unified LLMProvider interface
while retaining the existing RiskAssessmentProvider compatibility path.
"""

from typing import Dict, Type, Union

from .base import RiskAssessmentProvider
from .llm_base import LLMProvider


_REGISTRY: Dict[str, Type[Union[RiskAssessmentProvider, LLMProvider]]] = {}


def _normalize_name(name: str) -> str:
    """Normalize provider names across mock/openai/self_host naming styles."""
    key = (name or "mock").strip().lower()
    if key in {"self-host", "self_host", "selfhost"}:
        return "self_host"
    return key


def register_provider(name: str, provider_cls: Type[Union[RiskAssessmentProvider, LLMProvider]]) -> None:
    """Register a provider class by a stable name."""
    _REGISTRY[_normalize_name(name)] = provider_cls


def has_provider(name: str) -> bool:
    """Check whether a provider name is registered (or natively supported).

    A provider is considered available if it has been explicitly registered
    with ``register_provider()``, or if it is one of the built-in names
    (mock, openai, self_host).

    Parameters
    ----------
    name : str
        Provider name (e.g. ``"mock"``, ``"openai"``, ``"self_host"``).

    Returns
    -------
    bool
        ``True`` if the provider is available, ``False`` otherwise.
    """
    key = _normalize_name(name)
    if key in _REGISTRY:
        return True
    # Built-in names that are always available
    if key in {"mock", "openai", "self_host"}:
        return True
    return False


def get_provider(name: str = "mock") -> Union[RiskAssessmentProvider, LLMProvider]:
    """Return an instantiated provider object, defaulting to mock.

    Falls back to mock if the requested provider is not registered.
    Recognized aliases: mock, openai, self_host/self-host/selfhost.
    """
    key = _normalize_name(name)
    cls = _REGISTRY.get(key)
    if cls is None:
        if key == "openai":
            from .openai import OpenAIProvider
            return OpenAIProvider()
        if key == "self_host":
            from .self_host import SelfHostProvider
            return SelfHostProvider()
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

try:
    from .openai import OpenAIProvider
    register_provider("openai", OpenAIProvider)
except Exception:
    pass

try:
    from .self_host import SelfHostProvider
    register_provider("self_host", SelfHostProvider)
except Exception:
    pass