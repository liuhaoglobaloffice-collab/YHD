"""
Provider Gateway - Unified abstraction layer for AI model providers.

Enforces: Provider ≠ Agent
All model calls must go through this gateway.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import Mock
from uuid import UUID, uuid4

from ..core.errors import (
    ConfigurationError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)
from ..identity.audit import AuditService
from ..security.secrets import SecretsManager

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported AI providers."""

    OPENAI = "openai"
    XAI = "xai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"
    MOONSHOT = "moonshot"
    OLLAMA = "ollama"  # Week 4: 本地 LLM


class ProviderStatus(str, Enum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


@dataclass
class ModelConfig:
    """Model configuration."""

    provider: ProviderType
    model_id: str
    model_name: str
    context_window: int
    supports_streaming: bool = True
    supports_functions: bool = True
    supports_vision: bool = False
    input_cost_per_1k: float = 0.0  # USD per 1K tokens
    output_cost_per_1k: float = 0.0
    max_tokens: Optional[int] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Provider configuration."""

    provider: ProviderType
    api_key_name: str  # Reference to secret, never the actual key
    base_url: Optional[str] = None
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    rate_limit_rpm: Optional[int] = None  # Requests per minute
    rate_limit_tpm: Optional[int] = None  # Tokens per minute
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    """Token usage statistics."""

    input_tokens: int
    output_tokens: int
    total_tokens: int

    @property
    def cost(self) -> float:
        """Calculate estimated cost (requires model config)."""
        return 0.0  # Will be calculated by gateway with model config


@dataclass
class ProviderRequest:
    """Provider API request."""

    request_id: UUID
    trace_id: UUID
    provider: ProviderType
    model_id: str
    messages: List[Dict[str, Any]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    functions: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ProviderResponse:
    """Provider API response."""

    request_id: UUID
    trace_id: UUID
    provider: ProviderType
    model_id: str
    content: str
    usage: TokenUsage
    finish_reason: str
    response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ProviderMetrics:
    """Provider metrics."""

    provider: ProviderType
    status: ProviderStatus
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time_ms: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    error_message: Optional[str] = None


class BaseProvider(ABC):
    """Base class for all AI providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_type = config.provider
        self._metrics = ProviderMetrics(
            provider=self.provider_type,
            status=ProviderStatus.HEALTHY if config.enabled else ProviderStatus.DISABLED,
        )
        self._rate_limit_tokens: List[datetime] = []

    @abstractmethod
    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute completion request."""
        pass

    async def health_check(self) -> ProviderStatus:
        """Check provider health."""
        if not self.config.enabled:
            return ProviderStatus.DISABLED

        try:
            # Simple health check - attempt minimal request
            test_request = ProviderRequest(
                request_id=uuid4(),
                trace_id=uuid4(),
                provider=self.provider_type,
                model_id="test",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            await asyncio.wait_for(self._execute_with_retry(test_request), timeout=10.0)
            self._metrics.status = ProviderStatus.HEALTHY
            return ProviderStatus.HEALTHY
        except asyncio.TimeoutError:
            self._metrics.status = ProviderStatus.DEGRADED
            return ProviderStatus.DEGRADED
        except Exception as e:
            logger.warning(f"Provider {self.provider_type} health check failed: {e}")
            self._metrics.status = ProviderStatus.UNAVAILABLE
            return ProviderStatus.UNAVAILABLE

    async def _execute_with_retry(self, request: ProviderRequest) -> ProviderResponse:
        """Execute request with retry logic."""
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                # Rate limiting
                await self._check_rate_limit()

                # Execute request
                start_time = datetime.now(UTC)
                response = await self.complete(request)
                response_time_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
                response.response_time_ms = response_time_ms

                # Update metrics
                self._metrics.total_requests += 1
                self._metrics.successful_requests += 1
                self._metrics.total_tokens += response.usage.total_tokens
                self._metrics.last_success = datetime.now(UTC)

                # Update average response time
                total_successful = self._metrics.successful_requests
                avg = self._metrics.avg_response_time_ms
                self._metrics.avg_response_time_ms = (
                    avg * (total_successful - 1) + response_time_ms
                ) / total_successful

                return response

            except Exception as e:
                last_error = e
                self._metrics.total_requests += 1
                self._metrics.failed_requests += 1
                self._metrics.last_failure = datetime.now(UTC)
                self._metrics.error_message = str(e)

                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    delay = self.config.retry_delay_seconds * (2**attempt)
                    logger.warning(
                        f"Provider {self.provider_type} request failed (attempt {attempt + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Provider {self.provider_type} request failed after "
                        f"{self.config.max_retries} attempts: {e}"
                    )

        raise ExternalServiceError(
            f"Provider {self.provider_type} failed after {self.config.max_retries} attempts",
            details={"last_error": str(last_error)},
        )

    async def _check_rate_limit(self):
        """Check and enforce rate limits."""
        if not self.config.rate_limit_rpm:
            return

        now = datetime.now(UTC)
        # Remove old tokens (older than 1 minute)
        self._rate_limit_tokens = [
            ts for ts in self._rate_limit_tokens if (now - ts).total_seconds() < 60
        ]

        if len(self._rate_limit_tokens) >= self.config.rate_limit_rpm:
            # Wait until oldest token expires
            oldest = self._rate_limit_tokens[0]
            wait_seconds = 60 - (now - oldest).total_seconds()
            if wait_seconds > 0:
                logger.info(f"Rate limit reached for {self.provider_type}, waiting {wait_seconds}s")
                await asyncio.sleep(wait_seconds)

        self._rate_limit_tokens.append(now)

    def get_metrics(self) -> ProviderMetrics:
        """Get provider metrics."""
        return self._metrics


class ModelRegistry:
    """Registry for available models."""

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}

    def register(self, model: ModelConfig):
        """Register a model."""
        key = f"{model.provider}:{model.model_id}"
        self._models[key] = model
        logger.info(f"Registered model: {key}")

    def get(self, provider: ProviderType, model_id: str) -> ModelConfig:
        """Get model configuration."""
        key = f"{provider}:{model_id}"
        if key not in self._models:
            raise ResourceNotFoundError(f"Model not found: {key}", resource=f"model:{key}")

        model = self._models[key]
        if not model.enabled:
            raise ValidationError(f"Model is disabled: {key}", field="model_id", value=model_id)

        return model

    def list_models(
        self, provider: Optional[ProviderType] = None, enabled_only: bool = True
    ) -> List[ModelConfig]:
        """List available models."""
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if enabled_only:
            models = [m for m in models if m.enabled]

        return models

    def list_by_provider(self, provider: ProviderType) -> List[ModelConfig]:
        """List all models for a specific provider."""
        return [m for m in self._models.values() if m.provider == provider]


class ProviderGateway:
    """
    Unified gateway for all AI provider interactions.

    Enforces:
    - Security First: API keys never exposed
    - Fail Closed: Unknown providers/models denied
    - Audit Everything: All calls traced
    - Single Source of Truth: Only one gateway
    """

    def __init__(self, audit_service: AuditService):
        self._providers: Dict[ProviderType, BaseProvider] = {}
        self._provider_configs: Dict[ProviderType, ProviderConfig] = {}
        self._model_registry = ModelRegistry()
        self._audit_service = audit_service
        logger.info("Provider Gateway initialized")

    def register_provider(self, provider: BaseProvider):
        """
        Register a provider.

        Args:
            provider: Can be either a BaseProvider instance (immediate)
                     or a ProviderConfig (lazy initialization)
        """
        # Support both BaseProvider and ProviderConfig
        if isinstance(provider, ProviderConfig):
            # Lazy initialization: store config, create provider on first use
            provider_type = provider.provider
            if provider_type in self._provider_configs or provider_type in self._providers:
                raise ConfigurationError(
                    f"Provider already registered: {provider_type}",
                    field="provider",
                    value=str(provider_type),
                )
            self._provider_configs[provider_type] = provider
            logger.info(f"Registered provider config: {provider_type}")
        else:
            # Immediate: store provider instance
            provider_type = provider.provider_type
            if provider_type in self._providers:
                raise ConfigurationError(
                    f"Provider already registered: {provider_type}",
                    field="provider",
                    value=str(provider_type),
                )
            self._providers[provider_type] = provider
            logger.info(f"Registered provider: {provider_type}")

    def _get_or_create_provider(
        self, provider_type: ProviderType, secrets_manager: Optional[SecretsManager] = None
    ) -> BaseProvider:
        """
        Get provider instance, creating it lazily if needed.

        Args:
            provider_type: Type of provider to get
            secrets_manager: Optional secrets manager for lazy init

        Returns:
            Provider instance

        Raises:
            ResourceNotFoundError: If provider not registered
        """
        # Check if already instantiated
        if provider_type in self._providers:
            return self._providers[provider_type]

        # Check if config exists for lazy init
        if provider_type in self._provider_configs:
            config = self._provider_configs[provider_type]

            # Create provider from config
            if provider_type == ProviderType.OPENAI:
                provider = OpenAIProvider(config, secrets_manager or Mock())
            elif provider_type == ProviderType.ANTHROPIC:
                provider = AnthropicProvider(config, secrets_manager or Mock())
            elif provider_type == ProviderType.GOOGLE:
                provider = GoogleProvider(config, secrets_manager or Mock())
            elif provider_type == ProviderType.XAI:
                provider = XAIProvider(config, secrets_manager or Mock())
            elif provider_type == ProviderType.DEEPSEEK:
                provider = DeepSeekProvider(config, secrets_manager or Mock())
            elif provider_type == ProviderType.MOONSHOT:
                provider = MoonshotProvider(config, secrets_manager or Mock())
            else:
                raise ConfigurationError(
                    f"Unknown provider type: {provider_type}",
                    field="provider",
                    value=str(provider_type),
                )

            # Cache the instantiated provider
            self._providers[provider_type] = provider
            logger.info(f"Lazy initialized provider: {provider_type}")
            return provider

        # Provider not registered at all
        raise ResourceNotFoundError(
            f"Provider not registered: {provider_type}", resource=f"provider:{provider_type}"
        )

    def register_model(self, model: ModelConfig):
        """Register a model."""
        self._model_registry.register(model)

    async def complete(
        self,
        provider: ProviderType,
        model_id: str,
        messages: List[Dict[str, Any]],
        trace_id: UUID,
        actor_id: Optional[UUID] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProviderResponse:
        """
        Execute completion request through provider gateway.

        Security: API keys never exposed to callers.
        Audit: All requests logged.
        Fail Closed: Unknown provider/model denied.
        """
        # Validate provider exists
        if provider not in self._providers:
            await self._audit_service.log(
                action="provider_call_denied",
                status="denied",
                actor_id=actor_id,
                target_id=None,
                details={
                    "reason": "unknown_provider",
                    "provider": provider,
                    "trace_id": str(trace_id),
                },
            )
            raise ResourceNotFoundError(
                f"Provider not registered: {provider}", resource=f"provider:{provider}"
            )

        # Validate model exists
        try:
            model_config = self._model_registry.get(provider, model_id)
        except ResourceNotFoundError:
            await self._audit_service.log(
                action="model_call_denied",
                status="denied",
                actor_id=actor_id,
                target_id=None,
                details={
                    "reason": "unknown_model",
                    "provider": provider,
                    "model_id": model_id,
                    "trace_id": str(trace_id),
                },
            )
            raise

        # Create request
        request = ProviderRequest(
            request_id=uuid4(),
            trace_id=trace_id,
            provider=provider,
            model_id=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or model_config.max_tokens,
            stream=stream,
            functions=functions,
            metadata=metadata or {},
        )

        # Execute through provider
        provider_instance = self._get_or_create_provider(provider)

        try:
            response = await provider_instance._execute_with_retry(request)

            # Calculate cost
            cost = self._calculate_cost(model_config, response.usage)

            # Update provider metrics with cost
            provider_instance._metrics.total_cost += cost

            # Audit successful call
            await self._audit_service.log(
                action="provider_call_success",
                status="success",
                actor_id=actor_id,
                target_id=None,
                details={
                    "provider": provider,
                    "model_id": model_id,
                    "request_id": str(request.request_id),
                    "trace_id": str(trace_id),
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "cost_usd": cost,
                    "response_time_ms": response.response_time_ms,
                },
            )

            return response

        except Exception as e:
            # Audit failed call
            await self._audit_service.log(
                action="provider_call_failure",
                status="failure",
                actor_id=actor_id,
                target_id=None,
                details={
                    "provider": provider,
                    "model_id": model_id,
                    "request_id": str(request.request_id),
                    "trace_id": str(trace_id),
                    "error": str(e),
                },
            )
            raise

    def _calculate_cost(self, model: ModelConfig, usage: TokenUsage) -> float:
        """Calculate request cost."""
        input_cost = (usage.input_tokens / 1000.0) * model.input_cost_per_1k
        output_cost = (usage.output_tokens / 1000.0) * model.output_cost_per_1k
        return input_cost + output_cost

    async def get_provider_status(self, provider: ProviderType) -> ProviderStatus:
        """Get provider health status."""
        if provider not in self._providers and provider not in self._provider_configs:
            return ProviderStatus.UNAVAILABLE

        provider_instance = self._get_or_create_provider(provider)
        return await provider_instance.health_check()

    async def get_provider_statuses(self) -> Dict[ProviderType, ProviderStatus]:
        """Return health status for all configured providers."""
        statuses: Dict[ProviderType, ProviderStatus] = {}
        for provider in self.list_providers():
            try:
                statuses[provider] = await self.get_provider_status(provider)
            except Exception:
                statuses[provider] = ProviderStatus.UNAVAILABLE
        return statuses

    def get_provider_metrics(self, provider: ProviderType) -> ProviderMetrics:
        """Get provider metrics."""
        provider_instance = self._get_or_create_provider(provider)
        return provider_instance.get_metrics()

    def list_providers(self) -> List[ProviderType]:
        """List registered providers."""
        # Return both instantiated providers and registered configs
        all_providers = set(self._providers.keys()) | set(self._provider_configs.keys())
        return list(all_providers)

    def list_models(
        self, provider: Optional[ProviderType] = None, enabled_only: bool = True
    ) -> List[ModelConfig]:
        """List available models."""
        return self._model_registry.list_models(provider, enabled_only)


# ============================================================================
# Concrete Provider Implementations
# ============================================================================


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""

    def __init__(self, config: ProviderConfig, secrets_manager: SecretsManager):
        super().__init__(config)
        self._secrets_manager = secrets_manager
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI client with API key from secrets manager."""
        if self._client is None:
            try:
                import openai

                api_key = self._secrets_manager.get(self.config.api_key_name)
                self._client = openai.AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout_seconds,
                )
            except ImportError:
                raise ConfigurationError(
                    "OpenAI SDK not installed. Install with: pip install openai",
                    field="provider",
                    value="openai",
                )
        return self._client

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute OpenAI completion."""
        client = self._get_client()

        try:
            response = await client.chat.completions.create(
                model=request.model_id,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream,
                functions=request.functions,
            )

            choice = response.choices[0]

            return ProviderResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                provider=self.provider_type,
                model_id=request.model_id,
                content=choice.message.content or "",
                usage=TokenUsage(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                ),
                finish_reason=choice.finish_reason,
                response_time_ms=0.0,  # Set by retry wrapper
                metadata={"model": response.model, "id": response.id},
            )
        except Exception as e:
            raise ExternalServiceError(
                f"OpenAI API error: {str(e)}", details={"request_id": str(request.request_id)}
            )


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider implementation."""

    def __init__(self, config: ProviderConfig, secrets_manager: SecretsManager):
        super().__init__(config)
        self._secrets_manager = secrets_manager
        self._client = None

    def _get_client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                api_key = self._secrets_manager.get(self.config.api_key_name)
                self._client = anthropic.AsyncAnthropic(
                    api_key=api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout_seconds,
                )
            except ImportError:
                raise ConfigurationError(
                    "Anthropic SDK not installed. Install with: pip install anthropic",
                    field="provider",
                    value="anthropic",
                )
        return self._client

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute Anthropic completion."""
        client = self._get_client()

        try:
            # Convert messages to Anthropic format
            system_msg = None
            messages = []
            for msg in request.messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    messages.append(msg)

            kwargs = {
                "model": request.model_id,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 1024,
            }
            if system_msg:
                kwargs["system"] = system_msg

            response = await client.messages.create(**kwargs)

            content = response.content[0].text if response.content else ""

            return ProviderResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                provider=self.provider_type,
                model_id=request.model_id,
                content=content,
                usage=TokenUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                ),
                finish_reason=response.stop_reason or "stop",
                response_time_ms=0.0,
                metadata={"model": response.model, "id": response.id},
            )
        except Exception as e:
            raise ExternalServiceError(
                f"Anthropic API error: {str(e)}", details={"request_id": str(request.request_id)}
            )


class GoogleProvider(BaseProvider):
    """Google Gemini provider implementation."""

    def __init__(self, config: ProviderConfig, secrets_manager: SecretsManager):
        super().__init__(config)
        self._secrets_manager = secrets_manager
        self._client = None

    def _get_client(self):
        """Lazy-load Google client."""
        if self._client is None:
            try:
                import google.generativeai as genai

                api_key = self._secrets_manager.get(self.config.api_key_name)
                genai.configure(api_key=api_key)
                self._client = genai
            except ImportError:
                raise ConfigurationError(
                    "Google Generative AI SDK not installed. Install with: pip install google-generativeai",
                    field="provider",
                    value="google",
                )
        return self._client

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute Google Gemini completion."""
        genai = self._get_client()

        try:
            model = genai.GenerativeModel(request.model_id)

            # Convert messages to Gemini format
            prompt_parts = []
            for msg in request.messages:
                role = "user" if msg["role"] in ["user", "system"] else "model"
                prompt_parts.append(f"{role}: {msg['content']}")
            prompt = "\n".join(prompt_parts)

            response = await model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": request.temperature,
                    "max_output_tokens": request.max_tokens,
                },
            )

            # Estimate tokens (Gemini doesn't always provide exact counts)
            input_tokens = len(prompt) // 4  # Rough estimate
            output_tokens = len(response.text) // 4

            return ProviderResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                provider=self.provider_type,
                model_id=request.model_id,
                content=response.text,
                usage=TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                ),
                finish_reason="stop",
                response_time_ms=0.0,
                metadata={"model": request.model_id},
            )
        except Exception as e:
            raise ExternalServiceError(
                f"Google API error: {str(e)}", details={"request_id": str(request.request_id)}
            )


class GenericHTTPProvider(BaseProvider):
    """
    Generic HTTP provider for xAI, DeepSeek, and Moonshot.
    These providers use OpenAI-compatible APIs.
    """

    def __init__(self, config: ProviderConfig, secrets_manager: SecretsManager):
        super().__init__(config)
        self._secrets_manager = secrets_manager
        self._client = None

    def _get_client(self):
        """Lazy-load HTTP client."""
        if self._client is None:
            try:
                import httpx

                api_key = self._secrets_manager.get(self.config.api_key_name)
                self._client = httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=self.config.timeout_seconds,
                )
            except ImportError:
                raise ConfigurationError(
                    "httpx not installed. Install with: pip install httpx",
                    field="provider",
                    value=str(self.provider_type),
                )
        return self._client

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute OpenAI-compatible completion."""
        client = self._get_client()

        if not self.config.base_url:
            raise ConfigurationError(
                f"base_url required for {self.provider_type}", field="base_url", value=None
            )

        try:
            payload = {
                "model": request.model_id,
                "messages": request.messages,
                "temperature": request.temperature,
            }
            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens
            if request.stream:
                payload["stream"] = request.stream

            response = await client.post(f"{self.config.base_url}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            usage = data.get("usage", {})

            return ProviderResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                provider=self.provider_type,
                model_id=request.model_id,
                content=choice["message"]["content"] or "",
                usage=TokenUsage(
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                ),
                finish_reason=choice.get("finish_reason", "stop"),
                response_time_ms=0.0,
                metadata={"model": data.get("model"), "id": data.get("id")},
            )
        except Exception as e:
            raise ExternalServiceError(
                f"{self.provider_type} API error: {str(e)}",
                details={"request_id": str(request.request_id)},
            )


# Aliases for OpenAI-compatible providers
class XAIProvider(GenericHTTPProvider):
    """xAI Grok provider (OpenAI-compatible API)."""

    pass


class DeepSeekProvider(GenericHTTPProvider):
    """DeepSeek provider (OpenAI-compatible API)."""

    pass


class MoonshotProvider(GenericHTTPProvider):
    """Moonshot Kimi provider (OpenAI-compatible API)."""

    pass


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider implementation."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        # Ollama doesn't require API key for local instances
        self._host = config.base_url or "http://localhost:11434"

    def _get_client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import ollama

                self._client = ollama.AsyncClient(host=self._host)
            except ImportError:
                raise ConfigurationError(
                    "Ollama SDK not installed. Install with: pip install ollama",
                    field="provider",
                    value="ollama",
                )
        return self._client

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute Ollama completion."""
        client = self._get_client()

        try:
            # Convert messages format
            messages = []
            for msg in request.messages:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Ollama chat API call
            start_time = datetime.now(timezone.utc)
            response = await client.chat(
                model=request.model_id,
                messages=messages,
                options={
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens or -1,  # -1 means no limit
                },
                stream=False,  # Week 4 Day 1: Non-streaming first
            )
            end_time = datetime.now(timezone.utc)
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Extract response content
            content = response.get("message", {}).get("content", "")

            # Token usage (Ollama returns these in response)
            usage_data = response.get("usage", {})
            prompt_tokens = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)

            return ProviderResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                provider=self.provider_type,
                model_id=request.model_id,
                content=content,
                usage=TokenUsage(
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
                finish_reason=response.get("done_reason", "stop"),
                response_time_ms=response_time_ms,
                metadata={
                    "model": response.get("model", request.model_id),
                    "total_duration": response.get("total_duration", 0),
                    "load_duration": response.get("load_duration", 0),
                },
            )
        except Exception as e:
            raise ExternalServiceError(
                f"Ollama API error: {str(e)}",
                details={"request_id": str(request.request_id), "host": self._host}
            )
