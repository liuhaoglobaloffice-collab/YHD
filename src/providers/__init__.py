"""Provider adapter scaffold for supplier risk assessment and future AI providers.

Phase 2.1 exposes the unified LLM provider interface while keeping the
existing risk assessment provider compatibility path in place.
"""

from .base import RiskAssessmentProvider
from .llm_base import LLMProvider
from .mock import MockRiskAssessmentProvider
from .openai import OpenAIProvider
from .self_host import SelfHostProvider
from .registry import get_provider, register_provider

__all__ = [
    "RiskAssessmentProvider",
    "LLMProvider",
    "MockRiskAssessmentProvider",
    "OpenAIProvider",
    "SelfHostProvider",
    "get_provider",
    "register_provider",
]
