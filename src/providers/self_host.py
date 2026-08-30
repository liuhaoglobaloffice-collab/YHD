"""Self-host provider adapter for Phase 2.1 - Real Ollama calls.

Replaces the Phase 2.1 scaffold with a real Ollama provider that uses the
existing `ollama` Python SDK. Configuration is read from the Settings system
(OLLAMA_HOST, OLLAMA_DEFAULT_MODEL, ollama_timeout).

Ollama must be running and accessible at the configured host for chat/generate
calls to succeed. Embeddings require the Ollama server to be started with the
``--embeddings`` flag (501 otherwise).
"""

from __future__ import annotations

import asyncio
from typing import Any, List

import ollama

from src.core.config import get_settings
from .llm_base import LLMProvider


class SelfHostProvider(LLMProvider):
    """Local/self-hosted provider that calls Ollama API.

    Uses the existing ``ollama`` Python SDK. Configuration is read from the
    Settings system (OLLAMA_HOST, OLLAMA_DEFAULT_MODEL, ollama_timeout).
    """

    name = "self_host"

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        settings = get_settings()
        self._host = host or settings.ollama_host
        self._model = model or settings.ollama_default_model
        self._timeout = timeout or settings.ollama_timeout
        self._client: ollama.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # 本机/容器内地址：绝不路由到外部 HTTP 代理（否则 httpx 按
    # HTTP_PROXY/ALL_PROXY 环境变量把 localhost 请求发给代理，导致连接失败）
    _LOCAL_HOST_MARKERS = ("localhost", "127.0.0.1", "[::1]", "host.docker.internal")

    def _get_client(self) -> ollama.AsyncClient:
        """Lazy-load the Ollama async client."""
        if self._client is None:
            kwargs: dict[str, Any] = {}
            host_lower = (self._host or "").lower()
            if any(marker in host_lower for marker in self._LOCAL_HOST_MARKERS):
                kwargs["trust_env"] = False
            self._client = ollama.AsyncClient(host=self._host, **kwargs)
        return self._client

    async def health_check(self, timeout: float | None = None) -> dict:
        """Lightweight real connection check that does not run any business task.

        Calls the Ollama ``list models`` API (cheap metadata listing) to verify
        the server is reachable. Distinguishes:

        - ``healthy``: server reachable and responded successfully
        - ``unavailable``: connection refused / server not running
        - ``timeout``: server did not respond within the timeout window

        Returns
        -------
        dict
            ``{"provider": "self_host", "status": <str>, "detail": <str>}``
        """
        effective_timeout = timeout or min(self._timeout, 10)
        client = self._get_client()
        try:
            await asyncio.wait_for(client.list(), timeout=effective_timeout)
            return {
                "provider": "self_host",
                "status": "healthy",
                "detail": "",
            }
        except asyncio.TimeoutError:
            return {
                "provider": "self_host",
                "status": "timeout",
                "detail": f"no response within {effective_timeout}s from {self._host}",
            }
        except Exception as e:
            return {
                "provider": "self_host",
                "status": "unavailable",
                "detail": f"cannot connect to {self._host}: {e}",
            }

    def _raise(self, context: str, exc: Exception) -> None:
        """Wrap an exception with a provider-aware diagnostic message."""
        raise RuntimeError(
            f"Ollama {context} [provider=self_host, model={self._model}, "
            f"host={self._host}]: {exc}"
        ) from exc

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Call the Ollama chat API and return the assistant reply.

        Raises
        ------
        RuntimeError
            If Ollama is unreachable, the model is not found, or any other
            API error occurs. The message includes the provider name, model,
            and host for diagnostics.
        """
        client = self._get_client()
        try:
            response = await asyncio.wait_for(
                client.chat(
                    model=kwargs.get("model", self._model),
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": kwargs.get("temperature", 0.7),
                        "num_predict": kwargs.get("max_tokens", 2048),
                    },
                    stream=False,
                ),
                timeout=self._timeout,
            )
            return response.get("message", {}).get("content", "")
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Ollama chat timeout after {self._timeout}s "
                f"[provider=self_host, model={self._model}]"
            )
        except ollama.ResponseError as e:
            self._raise("API error", e)
        except Exception as e:
            self._raise("connection error", e)

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Call the Ollama generate API and return the response text.

        Raises
        ------
        RuntimeError
            If Ollama is unreachable, the model is not found, or any other
            API error occurs. The message includes the provider name, model,
            and host for diagnostics.
        """
        client = self._get_client()
        try:
            response = await asyncio.wait_for(
                client.generate(
                    model=kwargs.get("model", self._model),
                    prompt=prompt,
                    options={
                        "temperature": kwargs.get("temperature", 0.7),
                        "num_predict": kwargs.get("max_tokens", 2048),
                    },
                    stream=False,
                ),
                timeout=self._timeout,
            )
            return response.get("response", "")
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Ollama generate timeout after {self._timeout}s "
                f"[provider=self_host, model={self._model}]"
            )
        except ollama.ResponseError as e:
            self._raise("API error", e)
        except Exception as e:
            self._raise("connection error", e)

    async def embeddings(self, text: str, **kwargs: Any) -> List[float]:
        """Call the Ollama embed API and return the embedding vector.

        .. note::
           This requires the Ollama server to be started with the
           ``--embeddings`` flag.  If the server returns a 501 status,
           a clear error message is raised.

        Raises
        ------
        RuntimeError
            If Ollama is unreachable, embeddings are not supported by the
            server, or any other API error occurs.
        """
        client = self._get_client()
        try:
            response = await asyncio.wait_for(
                client.embed(
                    model=kwargs.get("model", self._model),
                    input=text,
                    truncate=True,
                ),
                timeout=self._timeout,
            )
            if response.embeddings:
                return list(response.embeddings[0])
            return []
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Ollama embeddings timeout after {self._timeout}s "
                f"[provider=self_host, model={self._model}]"
            )
        except ollama.ResponseError as e:
            if e.status_code == 501:
                raise RuntimeError(
                    f"Ollama embeddings not supported "
                    f"[provider=self_host, model={self._model}]. "
                    f"Start Ollama with the ``--embeddings`` flag."
                ) from e
            self._raise("API error", e)
        except Exception as e:
            self._raise("embeddings error", e)