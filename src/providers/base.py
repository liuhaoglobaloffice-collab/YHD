"""Base abstract provider contract for AI-backed risk assessment adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class RiskAssessmentProvider(ABC):
    """Provider interface for a risk assessment adapter.

    ⚠️ 已弃用: 请使用 src.ai.providers.BaseProvider 替代。
       此接口仅保留用于向后兼容，将在后续版本中移除。

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
