"""Real OpenAI-compatible LLM provider.

Reads API key from OPENAI_API_KEY env var, base URL from OPENAI_BASE_URL
(defaults to https://api.openai.com/v1), and model from OPENAI_CHAT_MODEL
(defaults to gpt-4o-mini). Uses httpx for HTTP calls.

Error handling (P2-6):
- Missing API key raises a clear "unavailable" RuntimeError before any
  network call is attempted.
- Timeouts, connection errors, and HTTP status errors are mapped to
  diagnostic RuntimeError messages that include the provider name and model.
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

    def _check_configured(self) -> None:
        """Raise a clear error when the provider is not configured."""
        if not self.api_key:
            raise RuntimeError(
                "OpenAI provider unavailable: OPENAI_API_KEY is not configured "
                "[provider=openai]"
            )

    def _wrap_error(self, exc: Exception, context: str, model: str) -> RuntimeError:
        """Map an httpx exception to a diagnostic RuntimeError.

        The original exception is preserved as ``__cause__`` (same chaining
        semantics as ``raise ... from exc``).
        """
        if isinstance(exc, httpx.TimeoutException):
            error = RuntimeError(
                f"OpenAI {context} timeout [provider=openai, model={model}]: {exc}"
            )
        elif isinstance(exc, httpx.ConnectError):
            error = RuntimeError(
                f"OpenAI {context} connection error "
                f"[provider=openai, base_url={self.base_url}]: {exc}"
            )
        elif isinstance(exc, httpx.HTTPStatusError):
            error = RuntimeError(
                f"OpenAI {context} API error "
                f"[provider=openai, model={model}, "
                f"status={exc.response.status_code}]: {exc}"
            )
        else:
            error = RuntimeError(
                f"OpenAI {context} error [provider=openai, model={model}]: {exc}"
            )
        error.__cause__ = exc
        return error

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Call the chat completions endpoint and return the assistant reply.

        Raises
        ------
        RuntimeError
            If the API key is missing, the request times out, the connection
            fails, or the API returns an error status.
        """
        self._check_configured()
        model = kwargs.get("model", self.chat_model)
        messages = [{"role": "user", "content": prompt}]

        # If context was passed from RAG pipeline, inject it as system message
        context = kwargs.get("context")
        if context:
            messages.insert(0, {"role": "system", "content": f"Use the following context to answer the user's query:\n\n{context}"})

        body = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }

        try:
            resp = await self._client().post("/chat/completions", json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise self._wrap_error(e, "chat", model)
        except (KeyError, IndexError, ValueError) as e:
            raise RuntimeError(
                f"OpenAI chat returned an unexpected response format "
                f"[provider=openai, model={model}]: {e}"
            ) from e

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Use the chat endpoint for generation tasks."""
        return await self.chat(prompt, **kwargs)

    async def embeddings(self, text: str, **kwargs: Any) -> List[float]:
        """Call the embeddings endpoint and return the vector.

        Raises
        ------
        RuntimeError
            If the API key is missing, the request times out, the connection
            fails, or the API returns an error status.
        """
        self._check_configured()
        model = kwargs.get("model", self.embed_model)
        body = {
            "model": model,
            "input": text,
        }
        try:
            resp = await self._client().post("/embeddings", json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
        except httpx.HTTPError as e:
            raise self._wrap_error(e, "embeddings", model)
        except (KeyError, IndexError, ValueError) as e:
            raise RuntimeError(
                f"OpenAI embeddings returned an unexpected response format "
                f"[provider=openai, model={model}]: {e}"
            ) from e

    async def health_check(self, timeout: float = 10.0) -> dict:
        """Lightweight health check that does not execute any business task.

        Uses the ``GET /models`` endpoint (a cheap metadata listing) to verify
        real connectivity. Distinguishes:

        - ``healthy``: server reachable and responded successfully
        - ``unavailable``: not configured (missing API key) or connection failed
        - ``timeout``: server did not respond within the timeout window
        - ``error``: server responded with an error status or unexpected failure
        """
        if not self.api_key:
            return {
                "provider": "openai",
                "status": "unavailable",
                "detail": "OPENAI_API_KEY is not configured",
            }
        try:
            resp = await self._client().get("/models", timeout=timeout)
            resp.raise_for_status()
            return {
                "provider": "openai",
                "status": "healthy",
                "detail": "",
            }
        except httpx.TimeoutException:
            return {
                "provider": "openai",
                "status": "timeout",
                "detail": f"no response within {timeout}s",
            }
        except httpx.ConnectError:
            return {
                "provider": "openai",
                "status": "unavailable",
                "detail": f"cannot connect to {self.base_url}",
            }
        except httpx.HTTPStatusError as e:
            return {
                "provider": "openai",
                "status": "error",
                "detail": f"HTTP {e.response.status_code}",
            }
        except Exception as e:  # pragma: no cover - defensive
            return {
                "provider": "openai",
                "status": "error",
                "detail": str(e),
            }
