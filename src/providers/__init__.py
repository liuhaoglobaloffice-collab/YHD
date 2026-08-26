"""Provider adapter scaffold for supplier risk assessment and future AI providers."""

from .base import RiskAssessmentProvider
from .mock import MockRiskAssessmentProvider
from .registry import get_provider, register_provider

__all__ = [
    "RiskAssessmentProvider",
    "MockRiskAssessmentProvider",
    "get_provider",
    "register_provider",
]
