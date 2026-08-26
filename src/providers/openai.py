"""OpenAI-style provider adapter scaffold for Phase 2.1."""

from typing import Any, List

from .llm_base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Small OpenAI-compatible provider scaffold.

    The implementation intentionally keeps the response shapes deterministic so
    that tests can verify the provider switch contract without requiring a real
    external API key.
    """

    name = "openai"

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        return f"[openai] response for: {prompt}"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[openai] generated text for: {prompt}"

    async def embeddings(self, text: str, **kwargs: Any) -> List[float]:
        # Deterministic fallback vector for test environments.
        text_len = max(1, len(text))
        return [round(float(text_len % 10) / 10, 4), 0.3, 0.7]
