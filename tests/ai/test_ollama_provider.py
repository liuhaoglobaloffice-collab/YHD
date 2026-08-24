"""
Week 4 Day 1: Ollama Provider 单元测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.ai.providers import (
    OllamaProvider,
    ProviderConfig,
    ProviderType,
    ProviderRequest,
    ProviderResponse,
    TokenUsage,
)
from src.core.errors import ConfigurationError, ExternalServiceError


class TestOllamaProvider:
    """Ollama Provider 单元测试"""

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
    def provider(self, ollama_config):
        """Ollama provider 实例"""
        return OllamaProvider(ollama_config)

    def test_provider_initialization(self, provider, ollama_config):
        """测试 Provider 初始化"""
        assert provider.config == ollama_config
        assert provider.provider_type == ProviderType.OLLAMA
        assert provider._host == "http://localhost:11434"
        assert provider._client is None  # Lazy loading

    def test_get_client_lazy_loading(self, provider):
        """测试客户端惰性加载"""
        with patch("ollama.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # 第一次调用，创建客户端
            client1 = provider._get_client()
            assert client1 == mock_client
            mock_client_class.assert_called_once_with(host="http://localhost:11434")

            # 第二次调用，复用客户端
            client2 = provider._get_client()
            assert client2 == mock_client
            assert mock_client_class.call_count == 1  # 仍然只调用一次

    def test_get_client_import_error(self, provider):
        """测试 ollama 未安装时的错误处理"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'ollama'")):
            with pytest.raises(Exception) as exc_info:
                provider._get_client()
            
            # ConfigurationError or其他导入错误
            assert ("Ollama SDK not installed" in str(exc_info.value) or 
                    "ollama" in str(exc_info.value).lower())

    @pytest.mark.asyncio
    async def test_complete_success(self, provider):
        """测试成功的 completion 请求"""
        # Mock Ollama response
        mock_response = {
            "message": {"content": "Hello! How can I help you?"},
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "done_reason": "stop",
            "model": "qwen2.5:7b",
            "total_duration": 1500000000,  # 1.5s in nanoseconds
            "load_duration": 500000000,  # 0.5s
        }

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=ProviderType.OLLAMA,
                model_id="qwen2.5:7b",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7,
                max_tokens=100,
            )

            response = await provider.complete(request)

            # 验证响应
            assert isinstance(response, ProviderResponse)
            assert response.content == "Hello! How can I help you?"
            assert response.provider == ProviderType.OLLAMA
            assert response.model_id == "qwen2.5:7b"
            assert response.usage.input_tokens == 10
            assert response.usage.output_tokens == 20
            assert response.usage.total_tokens == 30
            assert response.finish_reason == "stop"
            assert response.metadata["model"] == "qwen2.5:7b"
            assert response.metadata["total_duration"] == 1500000000

            # 验证 API 调用
            mock_client.chat.assert_called_once()
            call_kwargs = mock_client.chat.call_args.kwargs
            assert call_kwargs["model"] == "qwen2.5:7b"
            assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]
            assert call_kwargs["options"]["temperature"] == 0.7
            assert call_kwargs["options"]["num_predict"] == 100

    @pytest.mark.asyncio
    async def test_complete_with_multiple_messages(self, provider):
        """测试多轮对话"""
        mock_response = {
            "message": {"content": "Sure, I can help with that."},
            "usage": {"prompt_tokens": 50, "completion_tokens": 30},
            "done_reason": "stop",
            "model": "qwen2.5:7b",
        }

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=ProviderType.OLLAMA,
                model_id="qwen2.5:7b",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What's 2+2?"},
                    {"role": "assistant", "content": "4"},
                    {"role": "user", "content": "Now multiply by 3"},
                ],
                temperature=0.5,
                max_tokens=50,
            )

            response = await provider.complete(request)

            assert response.content == "Sure, I can help with that."
            
            # 验证消息格式转换
            call_kwargs = mock_client.chat.call_args.kwargs
            assert len(call_kwargs["messages"]) == 4
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][3]["content"] == "Now multiply by 3"

    @pytest.mark.asyncio
    async def test_complete_no_max_tokens(self, provider):
        """测试未指定 max_tokens 时的行为"""
        mock_response = {
            "message": {"content": "Response"},
            "usage": {},
            "done_reason": "stop",
        }

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=ProviderType.OLLAMA,
                model_id="qwen2.5:7b",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=None,  # 未指定
            )

            await provider.complete(request)

            # 验证 num_predict = -1 (无限制)
            call_kwargs = mock_client.chat.call_args.kwargs
            assert call_kwargs["options"]["num_predict"] == -1

    @pytest.mark.asyncio
    async def test_complete_api_error(self, provider):
        """测试 API 错误处理"""
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(side_effect=Exception("Connection refused"))

        with patch.object(provider, "_get_client", return_value=mock_client):
            request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=ProviderType.OLLAMA,
                model_id="qwen2.5:7b",
                messages=[{"role": "user", "content": "Hello"}],
            )

            with pytest.raises(ExternalServiceError) as exc_info:
                await provider.complete(request)
            
            assert "Ollama API error" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)
            assert provider._host in str(exc_info.value.details)

    @pytest.mark.asyncio
    async def test_complete_empty_response(self, provider):
        """测试空响应的处理"""
        mock_response = {
            "message": {},  # 空消息
            "usage": {},
        }

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=ProviderType.OLLAMA,
                model_id="qwen2.5:7b",
                messages=[{"role": "user", "content": "Test"}],
            )

            response = await provider.complete(request)

            # 应该返回空字符串而不是抛出错误
            assert response.content == ""
            assert response.usage.total_tokens == 0

    def test_custom_host(self):
        """测试自定义主机配置"""
        config = ProviderConfig(
            provider=ProviderType.OLLAMA,
            api_key_name="",  # Ollama不需要API key
            enabled=True,
            base_url="http://192.168.1.100:11434",
        )
        provider = OllamaProvider(config)
        
        assert provider._host == "http://192.168.1.100:11434"

    def test_default_host(self):
        """测试默认主机配置"""
        config = ProviderConfig(
            provider=ProviderType.OLLAMA,
            api_key_name="",  # Ollama不需要API key
            enabled=True,
        )
        provider = OllamaProvider(config)
        
        assert provider._host == "http://localhost:11434"
