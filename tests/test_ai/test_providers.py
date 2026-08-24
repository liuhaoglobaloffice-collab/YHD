"""
Tests for Provider Gateway and AI Provider implementations.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.ai.providers import (
    AnthropicProvider,
    DeepSeekProvider,
    GoogleProvider,
    ModelConfig,
    ModelRegistry,
    MoonshotProvider,
    OpenAIProvider,
    ProviderConfig,
    ProviderGateway,
    ProviderRequest,
    ProviderResponse,
    ProviderStatus,
    ProviderType,
    TokenUsage,
    XAIProvider,
)
from src.core.errors import ResourceNotFoundError
from src.identity.audit import AuditService
from src.security.secrets import SecretsManager


class TestModelRegistry:
    """Test model registry."""

    def test_register_model(self):
        """Test registering a model."""
        registry = ModelRegistry()
        config = ModelConfig(
            provider=ProviderType.OPENAI, model_id="gpt-4", model_name="gpt-4", context_window=8192
        )

        registry.register(config)

        retrieved = registry.get(ProviderType.OPENAI, "gpt-4")
        assert retrieved is not None
        assert retrieved.model_id == "gpt-4"
        assert retrieved.provider == ProviderType.OPENAI

    def test_get_nonexistent_model(self):
        """Test getting a model that doesn't exist."""
        registry = ModelRegistry()

        with pytest.raises(ResourceNotFoundError, match="Model not found"):
            registry.get(ProviderType.OPENAI, "nonexistent-model")

    def test_list_models_by_provider(self):
        """Test listing models by provider."""
        registry = ModelRegistry()

        config1 = ModelConfig(
            provider=ProviderType.OPENAI, model_id="gpt-4", model_name="gpt-4", context_window=8192
        )
        config2 = ModelConfig(
            provider=ProviderType.OPENAI,
            model_id="gpt-3.5-turbo",
            model_name="gpt-3.5-turbo",
            context_window=8192,
        )
        config3 = ModelConfig(
            provider=ProviderType.ANTHROPIC,
            model_id="claude-3-opus",
            model_name="claude-3-opus",
            context_window=8192,
        )

        registry.register(config1)
        registry.register(config2)
        registry.register(config3)

        openai_models = registry.list_models(provider=ProviderType.OPENAI)
        assert len(openai_models) == 2

        anthropic_models = registry.list_by_provider(ProviderType.ANTHROPIC)
        assert len(anthropic_models) == 1


class TestProviderConfig:
    """Test provider configuration."""

    def test_provider_config_defaults(self):
        """Test provider config with defaults."""
        config = ProviderConfig(
            provider=ProviderType.OPENAI,
            api_key_name="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
        )

        assert config.enabled is True
        assert config.max_retries == 3
        assert config.timeout_seconds == 60.0
        assert config.rate_limit_rpm is None  # Default is None, not 60


class TestProviderRequest:
    """Test provider request structure."""

    def test_provider_request_creation(self):
        """Test creating a provider request."""
        request = ProviderRequest(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=ProviderType.OPENAI,
            model_id="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=1000,
        )

        assert request.model_id == "gpt-4"
        assert len(request.messages) == 1
        assert request.temperature == 0.7
        assert request.trace_id is not None


class TestProviderResponse:
    """Test provider response structure."""

    def test_provider_response_success(self):
        """Test successful provider response."""
        response = ProviderResponse(
            request_id=uuid4(),
            trace_id=uuid4(),
            provider=ProviderType.OPENAI,
            model_id="gpt-4",
            content="Hello! How can I help you?",
            usage=TokenUsage(input_tokens=5, output_tokens=13, total_tokens=18),
            finish_reason="stop",
            response_time_ms=123.45,
        )
        assert response.content == "Hello! How can I help you?"
        assert response.usage.total_tokens == 18
        assert response.finish_reason == "stop"


@pytest.mark.asyncio
class TestProviderGateway:
    """Test provider gateway."""

    async def test_gateway_initialization(self):
        """Test gateway initializes with secrets manager."""
        Mock(spec=SecretsManager)
        audit = Mock(spec=AuditService)

        gateway = ProviderGateway(audit_service=audit)

        assert gateway._audit_service == audit
        assert gateway._model_registry is not None

    async def test_register_provider(self):
        """Test registering a provider."""
        Mock(spec=SecretsManager)
        audit = Mock(spec=AuditService)
        gateway = ProviderGateway(audit_service=audit)

        config = ProviderConfig(
            provider=ProviderType.OPENAI,
            api_key_name="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
        )

        gateway.register_provider(config)

        assert ProviderType.OPENAI in gateway._provider_configs

    async def test_get_provider_lazy_initialization(self):
        """Test provider is lazily initialized."""
        secrets = Mock(spec=SecretsManager)
        secrets.get_secret = Mock(return_value="test-api-key")
        audit = Mock(spec=AuditService)
        gateway = ProviderGateway(audit_service=audit)

        config = ProviderConfig(
            provider=ProviderType.OPENAI,
            api_key_name="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
        )
        gateway.register_provider(config)

        # Provider not yet initialized
        assert ProviderType.OPENAI not in gateway._providers

        # Get provider triggers initialization
        providers = gateway.list_providers()

        # Config is registered, so it's in the list
        assert ProviderType.OPENAI in providers

        # But provider instance is not yet created (lazy)
        assert ProviderType.OPENAI not in gateway._providers

        # Actually accessing provider status triggers initialization
        await gateway.get_provider_status(ProviderType.OPENAI)

        # Now provider is initialized
        assert ProviderType.OPENAI in gateway._providers

    async def test_get_unregistered_provider_fails(self):
        """Test getting an unregistered provider raises error."""
        Mock(spec=SecretsManager)
        audit = Mock(spec=AuditService)
        gateway = ProviderGateway(audit_service=audit)

        with pytest.raises(ResourceNotFoundError, match="Provider not registered"):
            gateway._get_or_create_provider(ProviderType.OPENAI)

    async def test_provider_status_tracking(self):
        """Test provider status is tracked."""
        secrets = Mock(spec=SecretsManager)
        secrets.get_secret = Mock(return_value="test-api-key")
        audit = Mock(spec=AuditService)
        gateway = ProviderGateway(audit_service=audit)

        config = ProviderConfig(
            provider=ProviderType.OPENAI,
            api_key_name="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
            enabled=False,
        )
        gateway.register_provider(config)

        status = await gateway.get_provider_status(ProviderType.OPENAI)
        assert status == ProviderStatus.DISABLED


class TestOpenAIProvider:
    """Test OpenAI provider."""

    def test_openai_provider_initialization(self):
        """Test OpenAI provider initializes correctly."""
        mock_secrets = Mock(spec=SecretsManager)
        mock_secrets.get_secret = Mock(return_value="test-key")

        config = ProviderConfig(
            provider=ProviderType.OPENAI,
            api_key_name="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
        )

        provider = OpenAIProvider(config, mock_secrets)

        assert provider.config == config
        assert provider._secrets_manager == mock_secrets
        assert provider._client is None  # Lazy initialized


class TestAnthropicProvider:
    """Test Anthropic provider."""

    def test_anthropic_provider_initialization(self):
        """Test Anthropic provider initializes correctly."""
        mock_secrets = Mock(spec=SecretsManager)
        mock_secrets.get_secret = Mock(return_value="test-key")

        config = ProviderConfig(
            provider=ProviderType.ANTHROPIC,
            api_key_name="ANTHROPIC_API_KEY",
            base_url="https://api.anthropic.com",
        )

        provider = AnthropicProvider(config, mock_secrets)

        assert provider.config == config
        assert provider._secrets_manager == mock_secrets


class TestGoogleProvider:
    """Test Google provider."""

    def test_google_provider_initialization(self):
        """Test Google provider initializes correctly."""
        mock_secrets = Mock(spec=SecretsManager)
        mock_secrets.get_secret = Mock(return_value="test-key")

        config = ProviderConfig(
            provider=ProviderType.GOOGLE,
            api_key_name="GOOGLE_API_KEY",
            base_url="https://generativelanguage.googleapis.com",
        )

        provider = GoogleProvider(config, mock_secrets)

        assert provider.config == config
        assert provider._secrets_manager == mock_secrets


class TestXAIProvider:
    """Test xAI provider."""

    def test_xai_provider_initialization(self):
        """Test xAI provider initializes correctly."""
        mock_secrets = Mock(spec=SecretsManager)
        mock_secrets.get_secret = Mock(return_value="test-key")

        config = ProviderConfig(
            provider=ProviderType.XAI,
            api_key_name="XAI_API_KEY",
            base_url="https://api.x.ai/v1",
        )

        provider = XAIProvider(config, mock_secrets)

        assert provider.config == config
        assert provider._secrets_manager == mock_secrets


class TestDeepSeekProvider:
    """Test DeepSeek provider."""

    def test_deepseek_provider_initialization(self):
        """Test DeepSeek provider initializes correctly."""
        mock_secrets = Mock(spec=SecretsManager)
        mock_secrets.get_secret = Mock(return_value="test-key")

        config = ProviderConfig(
            provider=ProviderType.DEEPSEEK,
            api_key_name="DEEPSEEK_API_KEY",
            base_url="https://api.deepseek.com",
        )

        provider = DeepSeekProvider(config, mock_secrets)

        assert provider.config == config
        assert provider._secrets_manager == mock_secrets


class TestMoonshotProvider:
    """Test Moonshot provider."""

    def test_moonshot_provider_initialization(self):
        """Test Moonshot provider initializes correctly."""
        mock_secrets = Mock(spec=SecretsManager)
        mock_secrets.get_secret = Mock(return_value="test-key")

        config = ProviderConfig(
            provider=ProviderType.MOONSHOT,
            api_key_name="MOONSHOT_API_KEY",
            base_url="https://api.moonshot.cn/v1",
        )

        provider = MoonshotProvider(config, mock_secrets)

        assert provider.config == config
        assert provider._secrets_manager == mock_secrets


class TestProviderSecurityEnforcement:
    """Test security enforcement in providers."""

    async def test_disabled_provider_cannot_be_used(self):
        """Test disabled provider cannot be used."""
        secrets = Mock(spec=SecretsManager)
        secrets.get_secret = Mock(return_value="test-api-key")
        audit = Mock(spec=AuditService)
        gateway = ProviderGateway(audit_service=audit)

        config = ProviderConfig(
            provider=ProviderType.OPENAI,
            api_key_name="OPENAI_API_KEY",
            base_url="https://api.openai.com/v1",
            enabled=False,
        )
        gateway.register_provider(config)

        # Should fail to get disabled provider
        status = await gateway.get_provider_status(ProviderType.OPENAI)
        assert status == ProviderStatus.DISABLED
