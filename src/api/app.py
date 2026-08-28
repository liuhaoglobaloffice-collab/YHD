"""
FastAPI application initialization
"""

import os
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.api.dependencies.database import close_database, init_database
from src.api.routes import api_router
from src.core.config import get_settings
from src.core.errors import LiuHaoError
from src.core.errors import (
    ResourceNotFoundError,
    PermissionDeniedError,
    AuthenticationError,
    ValidationError as LiuHaoValidationError,
)
from src.core.lifecycle import get_lifecycle_manager

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    lifecycle = get_lifecycle_manager()
    await lifecycle.startup()

    # Initialize database
    await init_database()
    logger.info("database_initialized")

    # Initialize Provider Gateway and register LLM providers
    await _initialize_providers()
    logger.info("provider_gateway_initialized")

    # Seed default AI employees
    await _seed_default_employees()
    logger.info("default_employees_seeded")

    # Seed S5 market defaults (templates & skill packs)
    try:
        from src.api.dependencies.database import get_session_factory
        from src.evolve.market import MarketService

        async with get_session_factory()() as session:
            await MarketService(session).seed_defaults()
        logger.info("market_defaults_seeded")
    except Exception as e:
        logger.warning("market_seed_failed", error=str(e))

    logger.info("api_startup_complete")

    yield

    # Shutdown
    await close_database()
    await lifecycle.shutdown()
    logger.info("api_shutdown_complete")


async def _initialize_providers() -> None:
    """Register LLM providers and models with the Provider Gateway.

    Supports multiple providers via comma-separated LLM_PROVIDER list.
    E.g.: LLM_PROVIDER=openai,anthropic,ollama
    Each provider is only registered if its API key is configured.
    """
    from src.ai.agents import create_default_agents
    from src.ai.gateway import get_gateway
    from src.ai.providers import (
        AnthropicProvider,
        DeepSeekProvider,
        GoogleProvider,
        ModelConfig,
        MockProvider,
        MoonshotProvider,
        OllamaProvider,
        OpenAIProvider,
        ProviderConfig,
        ProviderType,
        XAIProvider,
    )

    gateway = get_gateway()

    raw = os.getenv("LLM_PROVIDER", "mock").lower().strip()
    provider_names = [p.strip() for p in raw.split(",") if p.strip()]

    default_agents = create_default_agents()
    agent_provider_types = {agent.provider for agent in default_agents}

    registered_any = False

    # ==================== Provider 注册表 ====================

    PROVIDER_SETUP = {
        "openai": {
            "type": ProviderType.OPENAI,
            "api_key_var": "OPENAI_API_KEY",
            "base_url_var": "OPENAI_BASE_URL",
            "model_var": "OPENAI_CHAT_MODEL",
            "default_model": "gpt-4o-mini",
            "default_base_url": "https://api.openai.com/v1",
            "context_window": 128000,
            "provider_cls": OpenAIProvider,
            "needs_secrets": True,
            "cost": (0.15, 0.60),
        },
        "anthropic": {
            "type": ProviderType.ANTHROPIC,
            "api_key_var": "ANTHROPIC_API_KEY",
            "base_url_var": "ANTHROPIC_BASE_URL",
            "model_var": "ANTHROPIC_CHAT_MODEL",
            "default_model": "claude-3-5-sonnet-20241022",
            "default_base_url": "https://api.anthropic.com/v1",
            "context_window": 200000,
            "provider_cls": AnthropicProvider,
            "needs_secrets": True,
            "cost": (3.0, 15.0),
        },
        "google": {
            "type": ProviderType.GOOGLE,
            "api_key_var": "GOOGLE_API_KEY",
            "base_url_var": "GOOGLE_BASE_URL",
            "model_var": "GOOGLE_CHAT_MODEL",
            "default_model": "gemini-1.5-flash",
            "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "context_window": 1048576,
            "provider_cls": GoogleProvider,
            "needs_secrets": True,
            "cost": (0.075, 0.30),
        },
        "deepseek": {
            "type": ProviderType.DEEPSEEK,
            "api_key_var": "DEEPSEEK_API_KEY",
            "base_url_var": "DEEPSEEK_BASE_URL",
            "model_var": "DEEPSEEK_CHAT_MODEL",
            "default_model": "deepseek-chat",
            "default_base_url": "https://api.deepseek.com/v1",
            "context_window": 65536,
            "provider_cls": DeepSeekProvider,
            "needs_secrets": True,
            "cost": (0.14, 0.28),
        },
        "xai": {
            "type": ProviderType.XAI,
            "api_key_var": "XAI_API_KEY",
            "base_url_var": "XAI_BASE_URL",
            "model_var": "XAI_CHAT_MODEL",
            "default_model": "grok-2",
            "default_base_url": "https://api.x.ai/v1",
            "context_window": 131072,
            "provider_cls": XAIProvider,
            "needs_secrets": True,
            "cost": (2.0, 10.0),
        },
        "moonshot": {
            "type": ProviderType.MOONSHOT,
            "api_key_var": "MOONSHOT_API_KEY",
            "base_url_var": "MOONSHOT_BASE_URL",
            "model_var": "MOONSHOT_CHAT_MODEL",
            "default_model": "moonshot-v1-8k",
            "default_base_url": "https://api.moonshot.cn/v1",
            "context_window": 8192,
            "provider_cls": MoonshotProvider,
            "needs_secrets": True,
            "cost": (0.12, 0.12),
        },
        "ollama": {
            "type": ProviderType.OLLAMA,
            "api_key_var": None,
            "base_url_var": "OLLAMA_HOST",
            "model_var": "OLLAMA_DEFAULT_MODEL",
            "default_model": "qwen2.5:3b",
            "default_base_url": "http://localhost:11434",
            "context_window": 32768,
            "provider_cls": OllamaProvider,
            "needs_secrets": False,
            "cost": (0, 0),
        },
    }

    for name in provider_names:
        setup = PROVIDER_SETUP.get(name)
        if not setup:
            logger.warning("unknown_provider_skipped", provider=name)
            continue

        api_key = os.getenv(setup["api_key_var"], "") if setup["api_key_var"] else ""
        base_url = os.getenv(setup["base_url_var"], setup["default_base_url"])
        model = os.getenv(setup["model_var"], setup["default_model"])

        # Check if provider is available
        if setup["needs_secrets"] and not api_key:
            logger.warning(
                "provider_skipped_no_api_key",
                provider=name,
                env_var=setup["api_key_var"],
            )
            continue

        # Ollama needs explicit enable
        if name == "ollama":
            ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
            if not ollama_enabled:
                logger.warning("ollama_not_enabled_skipped")
                continue

        registered_any = True
        ptype = setup["type"]

        # Register provider config (lazy init)
        provider_config = ProviderConfig(
            provider=ptype,
            api_key_name=setup["api_key_var"] or "",
            base_url=base_url.rstrip("/"),
            timeout_seconds=60,
            max_retries=3,
            enabled=True,
            metadata={"model": model},
        )
        try:
            gateway.register_provider(provider_config)
        except Exception:
            pass  # Already registered

        # Register the model
        input_cost, output_cost = setup["cost"]
        gateway.register_model(ModelConfig(
            provider=ptype,
            model_id=model,
            model_name=model,
            context_window=setup["context_window"],
            supports_streaming=True,
            supports_functions=(name != "ollama"),
            input_cost_per_1k=input_cost,
            output_cost_per_1k=output_cost,
            enabled=True,
        ))

        # Register models for all agent types
        for agent in default_agents:
            try:
                gateway.register_model(ModelConfig(
                    provider=ptype,
                    model_id=agent.model_id,
                    model_name=agent.model_id,
                    context_window=setup["context_window"],
                    supports_streaming=True,
                    supports_functions=True,
                    enabled=True,
                ))
            except Exception:
                pass

        logger.info(
            "provider_registered",
            provider=name,
            model=model,
            type=ptype.value,
        )

    # Fallback to mock if no real provider was configured
    if not registered_any:
        for ptype in agent_provider_types:
            mock_provider = MockProvider()
            mock_provider.provider_type = ptype
            try:
                gateway.register_provider(mock_provider)
            except Exception:
                pass
        logger.info("using_mock_provider", provider=raw)

    # Register models for all default agents
    for agent in default_agents:
        try:
            gateway.register_model(ModelConfig(
                provider=agent.provider,
                model_id=agent.model_id,
                model_name=agent.model_id,
                context_window=128000 if agent.provider == ProviderType.OPENAI else 32768,
                supports_streaming=True,
                supports_functions=True,
                enabled=True,
            ))
        except Exception:
            pass

    logger.info(
        "provider_initialization_complete",
        provider=raw,
        agents=len(default_agents),
    )


async def _seed_default_employees() -> None:
    """Create default AI employees if they don't exist."""
    from src.ai.agents import AgentType, create_default_agents
    from src.api.dependencies.database import get_session_factory
    from src.identity.audit import AuditService
    from src.identity.rbac import RBACService
    from src.workforce.employee import AIEmployeeService
    from src.workforce.models import Department, Position
    from src.workforce.registry import AIEmployeeRegistry

    # Map agent types to department/position
    agent_role_map = {
        AgentType.GPT: (Department.CEO_OFFICE, Position.CEO_ASSISTANT),
        AgentType.GROK: (Department.ANALYTICS, Position.BUSINESS_ANALYST),
        AgentType.CLAUDE: (Department.ENGINEERING, Position.SYSTEM_ENGINEER),
        AgentType.DEEPSEEK: (Department.ANALYTICS, Position.DATA_ANALYST),
        AgentType.GEMINI: (Department.RESEARCH, Position.MARKET_RESEARCHER),
        AgentType.KIMI: (Department.RESEARCH, Position.PRODUCT_RESEARCHER),
    }

    default_agents = create_default_agents()
    factory = get_session_factory()

    async with factory() as session:
        registry = AIEmployeeRegistry(session)
        rbac = RBACService(session)
        service = AIEmployeeService(
            registry=registry,
            rbac_service=rbac,
            audit_service=AuditService,
        )

        existing = await registry.list_employees()
        existing_names = {e.name for e in existing}

        for agent in default_agents:
            if agent.name in existing_names:
                continue

            dept, pos = agent_role_map.get(agent.agent_type, (Department.OPERATIONS, Position.TASK_MANAGER))

            try:
                await service.create_employee(
                    name=agent.name,
                    department=dept,
                    position=pos,
                    description=agent.description,
                    agent_type=agent.agent_type,
                    provider_config={
                        "provider": agent.provider.value,
                        "model": agent.model_id,
                        "temperature": agent.temperature,
                        "max_tokens": agent.max_tokens,
                    },
                )
                logger.info("seeded_employee", name=agent.name)
            except Exception as e:
                logger.warning("seed_employee_skipped", name=agent.name, error=str(e))

    logger.info("employee_seeding_complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="LiuHao AI OS",
        description="CEO-First Enterprise AI Operating System",
        version=__version__,
        lifespan=lifespan,
        debug=settings.app_debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # S6: 性能监控 - 慢请求日志（>500ms）
    @app.middleware("http")
    async def slow_request_monitor(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > 500:
            logger.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                elapsed_ms=round(elapsed_ms, 1),
            )
        response.headers["X-Response-Time-Ms"] = str(round(elapsed_ms, 1))
        return response

    # Exception handlers
    @app.exception_handler(LiuHaoError)
    async def liuhao_error_handler(request: Request, exc: LiuHaoError):
        """Handle LiuHao-specific errors"""
        # 映射错误类型到 HTTP 状态码
        if isinstance(exc, ResourceNotFoundError):
            http_status = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, PermissionDeniedError):
            http_status = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, AuthenticationError):
            http_status = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, LiuHaoValidationError):
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            http_status = status.HTTP_400_BAD_REQUEST

        return JSONResponse(
            status_code=http_status,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    # Include API routes
    app.include_router(api_router)

    # Expose Prometheus metrics at root /metrics as well as under /api/v1/metrics
    try:
        from src.api.routes import metrics as metrics_module
        app.include_router(metrics_module.router)
    except Exception:
        # if metrics module cannot be loaded, continue without it
        logger.info("metrics_router_not_loaded")

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "LiuHao AI OS",
            "version": __version__,
            "status": "running",
        }

    return app

