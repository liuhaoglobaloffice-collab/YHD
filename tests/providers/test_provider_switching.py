"""Tests for the unified LLM provider interface and registry switching.

Phase 2.1 validates that:
- The mock, openai, and self_host providers all satisfy the LLMProvider contract.
- The registry correctly instantiates the expected provider for each name.
- Provider switching (get_provider with different names) behaves as expected.
"""

import asyncio
import os

from src.providers.registry import get_provider, has_provider
from src.providers.llm_base import LLMProvider
from src.providers.openai import OpenAIProvider
from src.providers.self_host import SelfHostProvider


def test_provider_switching_contract_across_mock_openai_self_host():
    async def _run():
        # --- Mock provider ---
        mock_provider = get_provider("mock")
        assert isinstance(mock_provider, LLMProvider)
        assert await mock_provider.chat("hello") == "[mock] reply for: hello"
        assert await mock_provider.generate("hello") == "[mock] generated text for: hello"
        assert await mock_provider.embeddings("hello") == [0.1, 0.2, 0.3]

        # --- OpenAI provider (skip real API when no key configured) ---
        openai_provider = get_provider("openai")
        assert isinstance(openai_provider, LLMProvider)
        assert isinstance(openai_provider, OpenAIProvider)
        # Skip real API calls when no API key is configured
        if os.getenv("OPENAI_API_KEY"):
            assert await openai_provider.chat("hello") == "[openai] response for: hello"
            assert await openai_provider.generate("hello") == "[openai] generated text for: hello"
            assert isinstance(await openai_provider.embeddings("hello"), list)

        # --- Self-host provider (real Ollama) ---
        self_host_provider = get_provider("self_host")
        assert isinstance(self_host_provider, LLMProvider)
        assert isinstance(self_host_provider, SelfHostProvider)

        # Real Ollama call (chat)
        chat_result = await self_host_provider.chat("Say hello in one word")
        assert isinstance(chat_result, str)
        assert len(chat_result) > 0
        # Should not be the old scaffold response
        assert "[self_host]" not in chat_result

        # Real Ollama call (generate)
        gen_result = await self_host_provider.generate("Say hello in one word")
        assert isinstance(gen_result, str)
        assert len(gen_result) > 0
        assert "[self_host]" not in gen_result

        # Real Ollama call (embeddings - may fail if server doesn't support it)
        try:
            emb_result = await self_host_provider.embeddings("hello")
            assert isinstance(emb_result, list)
            if emb_result:
                assert all(isinstance(v, float) for v in emb_result)
        except RuntimeError as e:
            # Acceptable: server may not support embeddings
            assert "not supported" in str(e) or "error" in str(e)

    asyncio.run(_run())


def test_has_provider():
    """Verify the has_provider predicate works for all built-in names."""
    assert has_provider("mock") is True
    assert has_provider("openai") is True
    assert has_provider("self_host") is True
    assert has_provider("self-host") is True
    assert has_provider("selfhost") is True

    # Unknown provider names
    assert has_provider("nonexistent") is False
    assert has_provider("") is True  # normalized to "mock"
    assert has_provider(None) is True  # normalized to "mock"


def test_get_provider_default_is_mock():
    """Default provider (no args) returns the mock provider."""
    provider = get_provider()
    assert isinstance(provider, LLMProvider)
    assert provider.name == "mock"


def test_get_provider_unknown_falls_back_to_mock():
    """Unknown provider names fall back to mock."""
    provider = get_provider("nonexistent_provider_xyz")
    assert isinstance(provider, LLMProvider)
    assert provider.name == "mock"