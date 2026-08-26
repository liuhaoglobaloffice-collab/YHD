import asyncio

from src.providers.registry import get_provider
from src.providers.llm_base import LLMProvider
from src.providers.openai import OpenAIProvider
from src.providers.self_host import SelfHostProvider


def test_provider_switching_contract_across_mock_openai_self_host():
    async def _run():
        mock_provider = get_provider("mock")
        assert isinstance(mock_provider, LLMProvider)
        assert await mock_provider.chat("hello") == "[mock] reply for: hello"
        assert await mock_provider.generate("hello") == "[mock] generated text for: hello"
        assert await mock_provider.embeddings("hello") == [0.1, 0.2, 0.3]

        openai_provider = get_provider("openai")
        assert isinstance(openai_provider, LLMProvider)
        assert isinstance(openai_provider, OpenAIProvider)
        assert await openai_provider.chat("hello") == "[openai] response for: hello"
        assert await openai_provider.generate("hello") == "[openai] generated text for: hello"
        assert isinstance(await openai_provider.embeddings("hello"), list)

        self_host_provider = get_provider("self_host")
        assert isinstance(self_host_provider, LLMProvider)
        assert isinstance(self_host_provider, SelfHostProvider)
        assert await self_host_provider.chat("hello") == "[self_host] response for: hello"
        assert await self_host_provider.generate("hello") == "[self_host] generated text for: hello"
        assert isinstance(await self_host_provider.embeddings("hello"), list)

    asyncio.run(_run())
