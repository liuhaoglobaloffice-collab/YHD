"""Self-host provider adapter scaffold for Phase 2.1."""

from typing import Any, List

from .llm_base import LLMProvider


class SelfHostProvider(LLMProvider):
    """Local/self-hosted provider scaffold.

    This intentionally avoids external network dependencies and provides a
    deterministic response contract for the Phase 2.1 test gate.
    """

    name = "self_host"

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        return f"[self_host] response for: {prompt}"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[self_host] generated text for: {prompt}"

    async def embeddings(self, text: str, **kwargs: Any) -> List[float]:
        text_len = max(1, len(text))
        return [0.2, round(float(text_len % 10) / 10, 4), 0.9]
