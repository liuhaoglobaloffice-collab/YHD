"""Base abstract provider contract for AI-backed risk assessment adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class RiskAssessmentProvider(ABC):
    """Provider interface for a risk assessment adapter.

    The agent may keep using the existing `_call_ai_analysis` mock path,
    but the adapter provides a consistent abstraction point for future
    integrations such as OpenAI, Claude, DeepSeek, or a local LLM.
    """

    name: str = "base"

    @abstractmethod
    async def analyze(self, prompt: str) -> str:
        """Return the raw AI response string for the given prompt."""

    def normalize(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optional normalization hook; adapters can return a dict or raw payload."""
        return payload or {}
