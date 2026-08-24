"""
Week 4 Day 2: Ollama Provider Gateway 集成测试

测试 OllamaProvider 是否正确集成到 ProviderGateway 中
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.ai.providers import (
    OllamaProvider,
    ProviderGateway,
    ProviderConfig,
    ProviderType,
    ProviderRequest,
    ProviderResponse,
    TokenUsage,
)
from src.security.secrets import SecretsManager


class TestOllamaProviderGatewayIntegration:
    """测试 Ollama Provider 在 Gateway 中的集成"""

    @pytest.fixture
    def secrets_manager(self):
        """Mock SecretsManager"""
        mock_sm = MagicMock()
        mock_sm.get = MagicMock(return_value="dummy_key")
        return mock_sm

    @pytest.fixture
    def ollama_config(self):
        """Ollama provider 配置"""
        return ProviderConfig(
            provider=ProviderType.OLLAMA,
            api_key_name="",  # Ollama不需要API key
            enabled=True,
            base_url="http://localhost:11434",
            timeout_seconds=60,
            max_retries=3,
        )

    @pytest.fixture
    def gateway(self, secrets_manager, ollama_config):
        """创建包含 Ollama 的 Gateway"""
        gateway = ProviderGateway(secrets_manager)
        
        # 手动注册 Ollama provider
        gateway.providers[ProviderType.OLLAMA] = OllamaProvider(ollama_config)
        
        return gateway

    def test_ollama_provider_registered(self, gateway):
        """测试 Ollama provider 是否注册"""
        assert ProviderType.OLLAMA in gateway.providers
        assert isinstance(gateway.providers[ProviderType.OLLAMA], OllamaProvider)

    @pytest.mark.asyncio
    async def test_gateway_route_to_ollama(self, gateway):
        """测试 Gateway 能否路由到 Ollama"""
        # Mock Ollama response
        mock_response = ProviderResponse(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=ProviderType.OLLAMA,
            model_id="qwen2.5:7b",
            content="Hello from Ollama!",
            usage=TokenUsage(input_tokens=5, output_tokens=10, total_tokens=15),
            finish_reason="stop",
            response_time_ms=500.0,
            metadata={},
        )

        # Mock the complete method
        with patch.object(
            gateway.providers[ProviderType.OLLAMA],
            "complete",
            new=AsyncMock(return_value=mock_response),
        ):
            request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=ProviderType.OLLAMA,
                model_id="qwen2.5:7b",
                messages=[{"role": "user", "content": "Hello"}],
            )

            response = await gateway.route(request)

            assert response.provider == ProviderType.OLLAMA
            assert response.content == "Hello from Ollama!"
            assert response.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_gateway_fallback_excludes_ollama(self, gateway):
        """测试 Gateway 降级策略（本地模型不参与云端降级）"""
        # 这个测试验证 Ollama 不会被用作其他provider的fallback
        # 因为本地模型应该独立使用
        
        request = ProviderRequest(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=ProviderType.OPENAI,  # 请求 OpenAI
            model_id="gpt-4",
            messages=[{"role": "user", "content": "Test"}],
        )

        # Gateway中只有Ollama provider
        # 这应该失败，因为Ollama不应该作为OpenAI的fallback
        with pytest.raises(Exception):
            await gateway.route(request)

    @pytest.mark.asyncio
    async def test_provider_config_from_settings(self):
        """测试从 Settings 加载 Ollama 配置"""
        from src.core.config import Settings

        settings = Settings(
            ollama_host="http://custom-host:11434",
            ollama_default_model="llama2:7b",
            ollama_timeout=120,
            ollama_enabled=True,
        )

        assert settings.ollama_host == "http://custom-host:11434"
        assert settings.ollama_default_model == "llama2:7b"
        assert settings.ollama_timeout == 120
        assert settings.ollama_enabled is True

    def test_ollama_provider_in_enum(self):
        """测试 ProviderType 枚举包含 OLLAMA"""
        assert hasattr(ProviderType, "OLLAMA")
        assert ProviderType.OLLAMA == "ollama"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, gateway):
        """测试并发请求处理"""
        mock_response = ProviderResponse(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=ProviderType.OLLAMA,
            model_id="qwen2.5:7b",
            content="Response",
            usage=TokenUsage(input_tokens=5, output_tokens=5, total_tokens=10),
            finish_reason="stop",
            response_time_ms=100.0,
            metadata={},
        )

        with patch.object(
            gateway.providers[ProviderType.OLLAMA],
            "complete",
            new=AsyncMock(return_value=mock_response),
        ):
            # 创建10个并发请求
            requests = [
                ProviderRequest(
                    request_id=uuid4(),
                    trace_id=uuid4(),
                    provider=ProviderType.OLLAMA,
                    model_id="qwen2.5:7b",
                    messages=[{"role": "user", "content": f"Request {i}"}],
                )
                for i in range(10)
            ]

            # 并发执行
            import asyncio
            responses = await asyncio.gather(
                *[gateway.route(req) for req in requests]
            )

            # 验证所有请求都成功
            assert len(responses) == 10
            assert all(r.provider == ProviderType.OLLAMA for r in responses)
