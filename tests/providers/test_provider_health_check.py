"""P2-6 Provider health check and error handling tests (Gaps 8 + 9).

Covers:
- healthy provider (mock provider + mocked OpenAI 200 response)
- unavailable provider (OpenAI without API key; Ollama connection refused)
- timeout (OpenAI ReadTimeout; Ollama asyncio.TimeoutError)
- connection error (OpenAI ConnectError)
- invalid configuration (missing API key on chat/embeddings)
- OpenAI error mapping (timeout / connection / HTTP status / other)
- /provider/status and /provider/status?check=true API endpoints

All OpenAI/Ollama network interactions are simulated with httpx.MockTransport
or stubbed clients — no real business task is ever executed.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.providers.mock import MockRiskAssessmentProvider
from src.providers.openai import OpenAIProvider
from src.providers.self_host import SelfHostProvider


def make_openai_provider(handler, api_key="test-key") -> OpenAIProvider:
    """Build an OpenAIProvider whose HTTP client uses a MockTransport."""
    provider = OpenAIProvider()
    provider.api_key = api_key
    provider._http_client = httpx.AsyncClient(
        base_url=provider.base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        transport=httpx.MockTransport(handler),
    )
    return provider


# ======================================================================
# OpenAI health check
# ======================================================================


def test_openai_health_check_healthy():
    provider = make_openai_provider(lambda request: httpx.Response(200, json={"data": []}))
    result = asyncio.run(provider.health_check())
    assert result["provider"] == "openai"
    assert result["status"] == "healthy"
    assert result["detail"] == ""


def test_openai_health_check_unavailable_without_api_key():
    """OpenAI without an API key must report unavailable (Gap 9)."""
    provider = OpenAIProvider()
    provider.api_key = ""
    result = asyncio.run(provider.health_check())
    assert result["status"] == "unavailable"
    assert "OPENAI_API_KEY" in result["detail"]


def test_openai_health_check_timeout():
    def handler(request):
        raise httpx.ReadTimeout("read timed out")

    provider = make_openai_provider(handler)
    result = asyncio.run(provider.health_check(timeout=2.0))
    assert result["status"] == "timeout"
    assert "2.0s" in result["detail"]


def test_openai_health_check_connection_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    provider = make_openai_provider(handler)
    result = asyncio.run(provider.health_check())
    assert result["status"] == "unavailable"
    assert "cannot connect" in result["detail"]


def test_openai_health_check_http_error_status():
    provider = make_openai_provider(lambda request: httpx.Response(500, json={}))
    result = asyncio.run(provider.health_check())
    assert result["status"] == "error"
    assert "500" in result["detail"]


# ======================================================================
# OpenAI error handling on chat / embeddings (Gap 8)
# ======================================================================


def test_openai_chat_without_api_key_raises_clear_error():
    provider = OpenAIProvider()
    provider.api_key = ""
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not configured"):
        asyncio.run(provider.chat("hello"))


def test_openai_embeddings_without_api_key_raises_clear_error():
    provider = OpenAIProvider()
    provider.api_key = ""
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not configured"):
        asyncio.run(provider.embeddings("hello"))


def test_openai_chat_timeout_is_wrapped_with_diagnostics():
    def handler(request):
        raise httpx.ReadTimeout("read timed out")

    provider = make_openai_provider(handler)
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(provider.chat("hello"))
    msg = str(exc_info.value)
    assert "timeout" in msg
    assert "provider=openai" in msg
    assert exc_info.value.__cause__ is not None


def test_openai_chat_connection_error_is_wrapped():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    provider = make_openai_provider(handler)
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(provider.chat("hello"))
    msg = str(exc_info.value)
    assert "connection error" in msg
    assert "provider=openai" in msg


def test_openai_chat_api_error_includes_status():
    provider = make_openai_provider(lambda request: httpx.Response(429, json={}))
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(provider.chat("hello"))
    msg = str(exc_info.value)
    assert "API error" in msg
    assert "status=429" in msg


def test_openai_chat_unexpected_response_format():
    provider = make_openai_provider(lambda request: httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(RuntimeError, match="unexpected response format"):
        asyncio.run(provider.chat("hello"))


def test_openai_embeddings_error_wrapped():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    provider = make_openai_provider(handler)
    with pytest.raises(RuntimeError, match="connection error"):
        asyncio.run(provider.embeddings("hello"))


def test_openai_chat_success_returns_content():
    provider = make_openai_provider(
        lambda request: httpx.Response(
            200, json={"choices": [{"message": {"content": "hi there"}}]}
        )
    )
    result = asyncio.run(provider.chat("hello"))
    assert result == "hi there"


# ======================================================================
# SelfHost (Ollama) health check
# ======================================================================


def _stub_self_host(client_stub) -> SelfHostProvider:
    provider = SelfHostProvider()
    provider._client = client_stub
    return provider


def test_self_host_health_check_healthy():
    client = MagicMock()
    client.list = AsyncMock(return_value={"models": []})
    provider = _stub_self_host(client)
    result = asyncio.run(provider.health_check())
    assert result["provider"] == "self_host"
    assert result["status"] == "healthy"
    assert result["detail"] == ""
    client.list.assert_awaited_once()


def test_self_host_health_check_connection_refused():
    """Ollama not running must report unavailable, not raise (Gap 9)."""
    client = MagicMock()
    client.list = AsyncMock(side_effect=ConnectionRefusedError("refused"))
    provider = _stub_self_host(client)
    result = asyncio.run(provider.health_check())
    assert result["status"] == "unavailable"
    assert "cannot connect" in result["detail"]


def test_self_host_health_check_timeout():
    async def slow_list():
        await asyncio.sleep(10)

    client = MagicMock()
    client.list = slow_list
    provider = _stub_self_host(client)
    result = asyncio.run(provider.health_check(timeout=0.05))
    assert result["status"] == "timeout"
    assert "0.05s" in result["detail"]


def test_self_host_health_check_real_unreachable_host():
    """Real connection attempt to an unused port reports unavailable."""
    provider = SelfHostProvider(host="http://127.0.0.1:16384")
    result = asyncio.run(provider.health_check(timeout=1))
    assert result["status"] in ("unavailable", "timeout")
    assert result["provider"] == "self_host"


# ======================================================================
# Mock provider health check
# ======================================================================


def test_mock_provider_health_check_healthy():
    provider = MockRiskAssessmentProvider()
    result = asyncio.run(provider.health_check())
    assert result["provider"] == "mock"
    assert result["status"] == "healthy"


# ======================================================================
# Provider status API endpoint (Gap 9)
# ======================================================================


def test_provider_status_endpoint_base_shape():
    from src.api.app import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/provider/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert "providers" in data
    assert "using_mock" in data
    # Base response must not perform network calls (no health_checks key)
    assert "health_checks" not in data


def test_provider_status_endpoint_with_check_returns_health_checks():
    """?check=true must attach real health check results for each provider."""
    from src.api.app import create_app

    app = create_app()
    client = TestClient(app)

    ollama_result = {"provider": "self_host", "status": "healthy", "detail": ""}
    openai_result = {"provider": "openai", "status": "unavailable", "detail": "no key"}

    with patch(
        "src.providers.self_host.SelfHostProvider"
    ) as ollama_cls, patch(
        "src.providers.openai.OpenAIProvider"
    ) as openai_cls:
        ollama_cls.return_value.health_check = AsyncMock(return_value=ollama_result)
        openai_cls.return_value.health_check = AsyncMock(return_value=openai_result)

        resp = client.get("/api/v1/provider/status?check=true")

    assert resp.status_code == 200
    data = resp.json()
    checks = data["health_checks"]
    statuses = {c["type"]: c["status"] for c in checks}
    assert statuses["ollama"] == "healthy"
    assert statuses["openai"] == "unavailable"
    for check in checks:
        assert check["status"] in ("healthy", "unavailable", "timeout", "error")
        assert "detail" in check
