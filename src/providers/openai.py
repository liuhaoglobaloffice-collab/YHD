"""Real OpenAI-compatible LLM provider.

Reads API key from OPENAI_API_KEY env var, base URL from OPENAI_BASE_URL
(defaults to https://api.openai.com/v1), and model from OPENAI_CHAT_MODEL
(defaults to gpt-4o-mini). Uses httpx for HTTP calls.
"""

import os
from typing import Any, List

import httpx

from .llm_base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider that calls the real API."""

    name = "openai"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.embed_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        self._http_client: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._http_client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=60.0)
        return self._http_client

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Call the chat completions endpoint and return the assistant reply."""
        messages = [{"role": "user", "content": prompt}]

        # If context was passed from RAG pipeline, inject it as system message
        context = kwargs.get("context")
        if context:
            messages.insert(0, {"role": "system", "content": f"Use the following context to answer the user's query:\n\n{context}"})

        body = {
            "model": kwargs.get("model", self.chat_model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }

        resp = await self._client().post("/chat/completions", json=body)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Use the chat endpoint for generation tasks."""
        return await self.chat(prompt, **kwargs)

    async def embeddings(self, text: str, **kwargs: Any) -> List[float]:
        """Call the embeddings endpoint and return the vector."""
        body = {
            "model": kwargs.get("model", self.embed_model),
            "input": text,
        }
        resp = await self._client().post("/embeddings", json=body)
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]
