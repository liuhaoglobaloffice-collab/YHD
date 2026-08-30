"""Tests for the SelfHostProvider (real Ollama calls).

Phase 2.1 validates that:
- SelfHostProvider correctly makes real Ollama calls.
- Timeout, unavailable, and invalid model errors produce clear diagnostics.
- The provider can be constructed with custom configuration overrides.
"""

import asyncio
import os

import pytest

from src.providers.self_host import SelfHostProvider


# ======================================================================
# Real Ollama integration tests
# ======================================================================


@pytest.mark.asyncio
async def test_self_host_chat_returns_real_response():
    """Chat with a real Ollama model returns meaningful text."""
    provider = SelfHostProvider()
    result = await provider.chat("Say hello in one word")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "[self_host]" not in result  # not the old scaffold


@pytest.mark.asyncio
async def test_self_host_generate_returns_real_response():
    """Generate with a real Ollama model returns meaningful text."""
    provider = SelfHostProvider()
    result = await provider.generate("Say hello in one word")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "[self_host]" not in result  # not the old scaffold


@pytest.mark.asyncio
async def test_self_host_embeddings_returns_clear_error_when_unsupported():
    """Embeddings raise a clear error when the server doesn't support them."""
    provider = SelfHostProvider()
    with pytest.raises(RuntimeError) as exc_info:
        await provider.embeddings("hello")
    msg = str(exc_info.value)
    assert "not supported" in msg or "error" in msg
    # The error message should be diagnostic
    assert "self_host" in msg


# ======================================================================
# Error handling tests
# ======================================================================


@pytest.mark.asyncio
async def test_self_host_unavailable_host():
    """Connecting to an unreachable host raises a clear RuntimeError."""
    provider = SelfHostProvider(host="http://localhost:16384", timeout=1)
    with pytest.raises(RuntimeError) as exc_info:
        await provider.chat("hello")
    msg = str(exc_info.value)
    assert "self_host" in msg
    assert "timeout" in msg or "connection error" in msg or "error" in msg


@pytest.mark.asyncio
async def test_self_host_invalid_model():
    """Using a non-existent model raises a clear RuntimeError."""
    provider = SelfHostProvider(model="nonexistent-model-xyz", timeout=5)
    with pytest.raises(RuntimeError) as exc_info:
        await provider.chat("hello")
    msg = str(exc_info.value)
    assert "self_host" in msg
    assert "API error" in msg or "error" in msg


@pytest.mark.asyncio
async def test_self_host_timeout_short():
    """An extremely short timeout should raise a timeout error."""
    provider = SelfHostProvider(timeout=0.001)
    with pytest.raises(RuntimeError) as exc_info:
        await provider.chat("hello")
    msg = str(exc_info.value)
    assert "timeout" in msg.lower()
    assert "self_host" in msg


# ======================================================================
# Configuration tests
# ======================================================================


def test_self_host_custom_constructor_overrides():
    """Constructor overrides should take precedence over settings."""
    provider = SelfHostProvider(host="http://custom:11434", model="custom-model", timeout=30)
    assert provider._host == "http://custom:11434"
    assert provider._model == "custom-model"
    assert provider._timeout == 30


def test_self_host_defaults_from_settings():
    """Default values should come from the settings system."""
    provider = SelfHostProvider()
    assert provider._host == os.getenv("OLLAMA_HOST", "http://localhost:11434")
    assert provider._model == os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
    assert provider._timeout == 60  # default from settings