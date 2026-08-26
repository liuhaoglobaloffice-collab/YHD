"""Unified LLM provider interface introduced for Phase 2.1.

Keeps the existing Supplier Risk assessment provider compatibility layer in
src/providers/base.py intact, while providing a clean LLM-facing contract for
chat(), generate(), and embeddings() operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Sequence


class LLMProvider(ABC):
    """Minimal LLM provider interface for chat, generation, and embeddings.

    This interface is intentionally small and compatible with the repository's
    current provider registry design. Implementations can return simple Python
    objects or strings, and can be selected via provider registry names.
    """

    name: str = "base"

    @abstractmethod
    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Return a natural-language answer for a prompt."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a generated text artifact for a prompt."""

    @abstractmethod
    async def embeddings(self, text: str, **kwargs: Any) -> List[float]:
        """Return a deterministic embedding vector for a text snippet."""
