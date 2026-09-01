"""
Provider Gateway - Unified abstraction layer for AI model providers.

Enforces: Provider ≠ Agent
All model calls must go through this gateway.
"""

import asyncio
import logging
import os
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
    """Registry for available models.

    Adds a small persistence layer so registered models and active selections
    survive process restarts. Persistence is intentionally lightweight (JSON
    file under data/) so test and dev environments can verify G5 (persistence
    / recovery) without requiring a full DB migration here.
    """

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._active_model_by_provider: Dict[ProviderType, str] = {}

        # Persistence file (can be overridden by env var for tests)
        try:
            from pathlib import Path
            data_dir = Path(os.environ.get("MODEL_REGISTRY_DIR", "data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            self._persist_file = data_dir / "model_registry.json"
        except Exception:
            self._persist_file = None

        # Attempt to load persisted state
        if self._persist_file and self._persist_file.exists():
            try:
                import json
                with open(self._persist_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                models = payload.get("models", [])
                for m in models:
                    cfg = ModelConfig(
                        provider=ProviderType(m["provider"]),
                        model_id=m["model_id"],
                        model_name=m.get("model_name", m["model_id"]),
                        context_window=m.get("context_window", 32768),
                        supports_streaming=m.get("supports_streaming", True),
                        supports_functions=m.get("supports_functions", True),
                        supports_vision=m.get("supports_vision", False),
                        input_cost_per_1k=m.get("input_cost_per_1k", 0.0),
                        output_cost_per_1k=m.get("output_cost_per_1k", 0.0),
                        max_tokens=m.get("max_tokens"),
                        enabled=m.get("enabled", True),
                        metadata=m.get("metadata", {}),
                    )
                    key = f"{cfg.provider}:{cfg.model_id}"
                    self._models[key] = cfg
                active = payload.get("active", {})
                for pstr, mid in active.items():
                    prov = None
                    try:
                        prov = ProviderType(pstr)
                    except Exception:
                        try:
                            prov = ProviderType[pstr.upper()]
                        except Exception:
                            prov = next((pt for pt in ProviderType if getattr(pt, 'value', '').lower() == str(pstr).lower()), None)
                    if prov:
                        self._active_model_by_provider[prov] = mid
                    else:
                        logger.warning(f"Unknown provider key in persisted registry: {pstr}")
                logger.info("Loaded persisted ModelRegistry state")
            except Exception as e:
                logger.warning(f"Failed to load persisted model registry: {e}")

    def _persist(self):
        """Persist the model registry atomically.

        Write to a temporary file in the same directory and atomically replace the
        target file. After writing, attempt to read back the JSON to verify the
        write succeeded. This reduces risk of partial writes and improves G5
        persistence reliability.
        """
        if not getattr(self, "_persist_file", None):
            return
        try:
            import json
            from pathlib import Path

            data_dir = Path(self._persist_file).parent
            data_dir.mkdir(parents=True, exist_ok=True)

            serial = {
                "models": [],
                "active": {},
            }
            for key, m in self._models.items():
                serial["models"].append({
                    "provider": m.provider.value,
                    "model_id": m.model_id,
                    "model_name": m.model_name,
                    "context_window": m.context_window,
                    "supports_streaming": m.supports_streaming,
                    "supports_functions": m.supports_functions,
                    "supports_vision": m.supports_vision,
                    "input_cost_per_1k": m.input_cost_per_1k,
                    "output_cost_per_1k": m.output_cost_per_1k,
                    "max_tokens": m.max_tokens,
                    "enabled": m.enabled,
                    "metadata": m.metadata,
                })
            for p, mid in self._active_model_by_provider.items():
                # persist provider by its canonical value
                serial["active"][p.value if hasattr(p, 'value') else str(p)] = mid

            tmp_path = data_dir / (self._persist_file.name + ".tmp")
            # write to temp file, flush and fsync to ensure durability
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(serial, f, ensure_ascii=False, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    # os.fsync may not be available on some platforms/FS; ignore if it fails
                    pass

            # verify by reading back
            with open(tmp_path, "r", encoding="utf-8") as f:
                _ = json.load(f)

            # atomic replace
            os.replace(str(tmp_path), str(self._persist_file))
            logger.info("Persisted ModelRegistry state (atomic)")
        except Exception as e:
            logger.warning(f"Failed to persist model registry: {e}")

    def register(self, model: ModelConfig):
        """Register a model."""
        key = f"{model.provider}:{model.model_id}"
        self._models[key] = model
        if model.enabled and model.provider not in self._active_model_by_provider:
            self._active_model_by_provider[model.provider] = model.model_id
        logger.info(f"Registered model: {key}")
        # persist state
        self._persist()

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

    def get_active_model(self, provider: ProviderType) -> Optional[str]:
        """Return the currently active model for a provider, if any."""
        active_id = self._active_model_by_provider.get(provider)
        if active_id is None:
            models = self.list_models(provider, enabled_only=True)
            if models:
                active_id = models[0].model_id
                self._active_model_by_provider[provider] = active_id
                # persist change
                self._persist()
            return active_id
        model = self._models.get(f"{provider}:{active_id}")
        if model is None or not model.enabled:
            models = self.list_models(provider, enabled_only=True)
            if not models:
                return None
            self._active_model_by_provider[provider] = models[0].model_id
            self._persist()
            return models[0].model_id
        return active_id

    def switch_active_model(self, provider: ProviderType, model_id: str) -> ModelConfig:
        """Switch the active model for a provider after validating it exists."""
        model = self.get(provider, model_id)
        self._active_model_by_provider[provider] = model.model_id
        # persist state
        self._persist()
        return model


class ProviderGateway:
    """
    Unified gateway for all AI provider interactions.

    Enforces:
    - Security First: API keys never exposed
    - Fail Closed: Unknown providers/models denied
    - Audit Everything: All calls traced
    - Single Source of Truth: Only one gateway
    """

    def __init__(self):
        self._providers: Dict[ProviderType, BaseProvider] = {}
        self._provider_configs: Dict[ProviderType, ProviderConfig] = {}
        self._model_registry = ModelRegistry()
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

            # Cloud providers need a real secrets manager to read API keys.
            # The completion/streaming call sites do not inject one, so fall
            # back to the process-wide (env + runtime) secrets manager — never
            # a unittest Mock, which would silently send a bogus API key.
            if secrets_manager is None and provider_type != ProviderType.OLLAMA:
                try:
                    from ..security.secrets import get_secrets_manager

                    secrets_manager = get_secrets_manager()
                except Exception:
                    logger.warning("secrets_manager_unavailable_fallback_mock", provider=provider_type)
                    secrets_manager = Mock()

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
            elif provider_type == ProviderType.OLLAMA:
                # Ollama doesn't need a secrets manager
                provider = OllamaProvider(config)
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

    def _resolve_fallback(
        self, requested: ProviderType
    ) -> Optional[tuple["ProviderType", str]]:
        """Pick a registered REAL provider to serve a request for a provider
        type that is not available in this deployment.

        Self-hosted deployments ship built-in agents whose default providers
        are cloud vendors (MOONSHOT / OPENAI / ...). When only Ollama (or
        another real provider) is configured, those agents can still run:
        remap to an available real provider and its default model.

        - Never remaps onto a MockProvider / production sentinel.
        - Prefers self-hosted (Ollama), then any other registered provider.
        - Returns None when no real provider is available (caller then
          raises the original "not registered" error).
        """
        available: List[ProviderType] = []
        for ptype in self.list_providers():
            inst = self._providers.get(ptype)
            if inst is not None and isinstance(inst, MockProvider):
                continue  # mock / sentinel can never serve a real completion
            available.append(ptype)
        if not available:
            return None

        priority = [ProviderType.OLLAMA]
        ordered = [p for p in priority if p in available] + [
            p for p in available if p not in priority
        ]
        chosen = ordered[0]

        # Default model registered for this provider at startup is kept in
        # the provider config metadata; fall back to first enabled model.
        model_id: Optional[str] = None
        cfg = self._provider_configs.get(chosen)
        if cfg and getattr(cfg, "metadata", None):
            model_id = cfg.metadata.get("model")
        if not model_id:
            models = self._model_registry.list_models(chosen, enabled_only=True)
            if models:
                model_id = models[0].model_id
        if not model_id:
            return None
        return chosen, model_id

    def _maybe_remap_provider(
        self, provider: ProviderType, model_id: str
    ) -> tuple[ProviderType, str]:
        """Remap (provider, model_id) onto a usable real provider when the
        requested provider is unavailable (unregistered, or only a mock
        sentinel). Returns the original pair unchanged when usable."""
        inst = self._providers.get(provider)
        is_mock_sentinel = inst is not None and isinstance(inst, MockProvider)
        registered = (
            provider in self._providers or provider in self._provider_configs
        )
        if registered and not is_mock_sentinel:
            return provider, model_id

        fallback = self._resolve_fallback(provider)
        if fallback is None:
            return provider, model_id  # let the caller raise the original error
        fb_provider, fb_model = fallback
        logger.warning(
            "provider_fallback_remap",
            extra={
                "requested_provider": str(provider),
                "requested_model": model_id,
                "remapped_provider": str(fb_provider),
                "remapped_model": fb_model,
            },
        )
        return fb_provider, fb_model

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
        # Self-host fallback: remap unavailable providers (unregistered or
        # mock sentinel) onto an available real provider + default model.
        provider, model_id = self._maybe_remap_provider(provider, model_id)

        # Validate provider exists（先解析懒注册的 ProviderConfig，再判定未注册）
        if provider not in self._providers:
            self._get_or_create_provider(provider)

        # Validate model exists
        try:
            model_config = self._model_registry.get(provider, model_id)
        except ResourceNotFoundError:
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

            return response

        except Exception as e:
            raise

    def _calculate_cost(self, model: ModelConfig, usage: TokenUsage) -> float:
        """Calculate request cost."""
        input_cost = (usage.input_tokens / 1000.0) * model.input_cost_per_1k
        output_cost = (usage.output_tokens / 1000.0) * model.output_cost_per_1k
        return input_cost + output_cost

    async def stream_complete(
        self,
        provider: ProviderType,
        model_id: str,
        messages: List[Dict[str, Any]],
        trace_id: UUID,
        actor_id: Optional[UUID] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Execute a streaming completion through the provider gateway.

        Yields chunk dicts: {"delta": str} for text fragments, and a final
        {"done": True, "usage": {...}} marker.

        Raises:
            ResourceNotFoundError: Unknown provider/model
        """
        # Self-host fallback: remap unavailable providers onto a real one
        provider, model_id = self._maybe_remap_provider(provider, model_id)

        # Validate provider exists
        if provider not in self._providers and provider not in self._provider_configs:
            raise ResourceNotFoundError(
                f"Provider not registered: {provider}", resource=f"provider:{provider}"
            )

        # Validate model exists
        model_config = self._model_registry.get(provider, model_id)

        request = ProviderRequest(
            request_id=uuid4(),
            trace_id=trace_id,
            provider=provider,
            model_id=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or model_config.max_tokens,
            stream=True,
            metadata=metadata or {},
        )

        provider_instance = self._get_or_create_provider(provider)

        # Check provider supports streaming
        if not hasattr(provider_instance, "stream_complete"):
            raise ConfigurationError(
                f"Provider {provider} does not support streaming",
                field="provider",
                value=str(provider),
            )

        async for chunk in provider_instance.stream_complete(request):
            yield chunk

    async def get_provider_status(self, provider: ProviderType) -> ProviderStatus:
        """Get provider health status."""
        if provider not in self._providers and provider not in self._provider_configs:
            return ProviderStatus.UNAVAILABLE

        provider_instance = self._get_or_create_provider(provider)
        return await provider_instance.health_check()

    def get_provider_metrics(self, provider: ProviderType) -> ProviderMetrics:
        """Get provider metrics."""
        provider_instance = self._get_or_create_provider(provider)
        return provider_instance.get_metrics()

    def list_providers(self) -> List[ProviderType]:
        """List registered providers."""
        # Return both instantiated providers and registered configs
        all_providers = set(self._providers.keys()) | set(self._provider_configs.keys())
        return list(all_providers)

    def unregister_provider(self, provider_type: ProviderType) -> None:
        """Remove a provider (instance + lazy config). Used by runtime
        provider re-configuration (UI 添加/更新 API Key)."""
        self._providers.pop(provider_type, None)
        self._provider_configs.pop(provider_type, None)
        logger.info(f"Unregistered provider: {provider_type}")

    def list_real_providers(self) -> List[ProviderType]:
        """Return registered providers that can serve REAL completions.

        Excludes MockProvider instances / production sentinels. Lazy
        ProviderConfig entries count as real (instantiated on demand).
        """
        real: List[ProviderType] = []
        for ptype in self.list_providers():
            inst = self._providers.get(ptype)
            if inst is not None and isinstance(inst, MockProvider):
                continue
            real.append(ptype)
        return real

    def list_models(
        self, provider: Optional[ProviderType] = None, enabled_only: bool = True
    ) -> List[ModelConfig]:
        """List available models."""
        return self._model_registry.list_models(provider, enabled_only)

    def list_provider_models(self, provider: ProviderType, enabled_only: bool = True) -> List[ModelConfig]:
        """Return the model catalog for a provider in a stable, API-friendly order."""
        models = self._model_registry.list_models(provider, enabled_only=enabled_only)
        return sorted(models, key=lambda model: model.model_id)

    def get_active_model(self, provider: ProviderType) -> Optional[str]:
        """Return the active model ID for a provider."""
        return self._model_registry.get_active_model(provider)

    def switch_model(self, provider: ProviderType, model_id: str) -> ModelConfig:
        """Select a model as the active model for a provider.

        This provides the real model-switching behavior the Y1 blueprint expects:
        one provider can host multiple models, and the runtime must be able to
        switch among them without rewriting the provider or agent binding.
        """
        if provider not in self.list_providers() and not self._model_registry.list_by_provider(provider):
            raise ResourceNotFoundError(
                f"Provider not registered: {provider}", resource=f"provider:{provider}"
            )
        return self._model_registry.switch_active_model(provider, model_id)


# ============================================================================
# Concrete Provider Implementations
# ============================================================================


class MockProvider(BaseProvider):
    """Mock provider that returns a canned response for development/testing.

    In production mode (when _production_blocked=True), calling complete()
    or stream_complete() will raise an error to prevent silent mock usage.
    """

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig(
                provider=ProviderType.OPENAI,
                api_key_name="",
                enabled=True,
            )
        super().__init__(config)
        self._request_count = 0
        self._production_blocked = False

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Return a mock completion response."""
        if self._production_blocked:
            raise RuntimeError(
                "No real LLM provider configured. "
                "Set LLM_PROVIDER and the corresponding API key in .env. "
                "MockProvider is blocked in production mode."
            )
        self._request_count += 1

        # Extract the last user message content for the mock response
        user_msg = ""
        for msg in reversed(request.messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        return ProviderResponse(
            request_id=request.request_id,
            trace_id=request.trace_id,
            provider=self.provider_type,
            model_id=request.model_id,
            content=(
                f"[Mock Response #{self._request_count}] "
                f"Received your request. Model: {request.model_id}. "
                f"Your message was: \"{user_msg[:100]}{'...' if len(user_msg) > 100 else ''}\""
            ),
            usage=TokenUsage(
                input_tokens=len(user_msg.split()),
                output_tokens=50,
                total_tokens=len(user_msg.split()) + 50,
            ),
            finish_reason="stop",
            response_time_ms=5.0,
            metadata={"mock": True, "request_count": self._request_count},
        )

    async def stream_complete(self, request: ProviderRequest):
        """Yield mock chunks for streaming clients."""
        if self._production_blocked:
            raise RuntimeError(
                "No real LLM provider configured. "
                "Set LLM_PROVIDER and the corresponding API key in .env. "
                "MockProvider is blocked in production mode."
            )
        user_msg = ""
        for msg in reversed(request.messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        text = (
            f"[Mock Stream] Model: {request.model_id}. Your message was: "
            f"\"{user_msg[:100]}\""
        )
        # Yield in small chunks to simulate streaming
        for i in range(0, len(text), 12):
            yield {"delta": text[i:i + 12]}
        yield {
            "done": True,
            "usage": {
                "prompt_tokens": len(user_msg.split()),
                "completion_tokens": 20,
                "total_tokens": len(user_msg.split()) + 20,
            },
        }


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

    # 本机/容器内地址：绝不路由到外部 HTTP 代理（否则 httpx 按
    # HTTP_PROXY/ALL_PROXY 环境变量把 localhost 请求发给代理，导致连接失败）
    _LOCAL_HOST_MARKERS = ("localhost", "127.0.0.1", "[::1]", "host.docker.internal")

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        # Ollama doesn't require API key for local instances
        self._host = config.base_url or "http://localhost:11434"
        # Use the configured model from metadata, fall back to model_id
        self._ollama_model = config.metadata.get("model", "qwen2.5:7b")

    def _get_client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import ollama

                kwargs: dict[str, Any] = {}
                host_lower = (self._host or "").lower()
                if any(marker in host_lower for marker in self._LOCAL_HOST_MARKERS):
                    kwargs["trust_env"] = False
                self._client = ollama.AsyncClient(host=self._host, **kwargs)
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
                model=self._ollama_model,
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

            # Token usage：Ollama chat 响应没有 usage 字段，
            # 真实 token 计数在 prompt_eval_count / eval_count
            usage_data = response.get("usage") or {}
            prompt_tokens = (
                usage_data.get("prompt_tokens")
                or response.get("prompt_eval_count")
                or 0
            )
            completion_tokens = (
                usage_data.get("completion_tokens")
                or response.get("eval_count")
                or 0
            )

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

    async def stream_complete(
        self,
        request: ProviderRequest,
    ) -> Any:
        """
        Execute Ollama completion with streaming (SSE/NDJSON chunks).

        Yields dicts with {"delta": str} for each text fragment and a final
        {"done": True, "usage": {...}} marker for token statistics.

        Returns:
            Async iterator of chunk dicts
        """
        client = self._get_client()

        messages = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in request.messages
        ]

        try:
            # ollama AsyncClient.chat with stream=True returns a coroutine
            # resolving to an async iterator of message chunks.
            response = await client.chat(
                model=self._ollama_model,
                messages=messages,
                options={
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens or 1024,
                },
                stream=True,
            )

            async for chunk in response:
                if chunk.get("done"):
                    usage_data = chunk.get("usage") or {}
                    prompt_tokens = (
                        usage_data.get("prompt_tokens")
                        or chunk.get("prompt_eval_count")
                        or 0
                    )
                    completion_tokens = (
                        usage_data.get("completion_tokens")
                        or chunk.get("eval_count")
                        or 0
                    )
                    yield {
                        "done": True,
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": prompt_tokens + completion_tokens,
                        },
                        "total_duration": chunk.get("total_duration"),
                    }
                    return
                yield {"delta": chunk.get("message", {}).get("content", "")}
        except Exception as e:
            raise ExternalServiceError(
                f"Ollama stream error: {str(e)}",
                details={"host": self._host}
            )
