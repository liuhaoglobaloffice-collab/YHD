"""
Health check and system info endpoints
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src import __version__
from src.api.dependencies import get_current_user_optional
from src.api.dependencies.database import get_db
from src.api.schemas import HealthResponse, SystemInfoResponse
from src.core.config import get_settings
from src.core.lifecycle import get_lifecycle_manager
from src.identity.models import User
from src.scheduler import get_business_scheduler
from src.security.policy import get_policy_engine
from src.security.secrets import check_production_secrets

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns system status including provider status
    """
    settings = get_settings()
    lifecycle = get_lifecycle_manager()

    status = "healthy" if lifecycle.is_ready() else "unhealthy"

    # Get provider status
    from src.api.provider_catalog import get_system_provider_status
    provider = get_system_provider_status()

    logger.info("health_check", status=status, provider_configured=provider["configured"])

    return HealthResponse(
        status=status,
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        provider=provider,
    )


@router.get("/ready")
async def ready_check(
    session: AsyncSession = Depends(get_db),
):
    """
    Comprehensive readiness check (database connectivity + lifecycle).
    Used by Kubernetes/Docker health checks.
    """
    settings = get_settings()
    lifecycle = get_lifecycle_manager()
    checks = {"lifecycle": lifecycle.is_ready(), "database": False}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.warning("health_db_check_failed", error=str(e))

    # 业务调度器为可选组件（默认关闭），状态仅展示、不影响健康判定
    scheduler = get_business_scheduler()
    scheduler_status = scheduler.status() if scheduler else {
        "enabled": bool(settings.scheduler_enabled),
        "running": False,
        "interval_seconds": settings.scheduler_interval_seconds,
        "auto_activate": bool(settings.scheduler_auto_activate),
        "runs": 0,
        "last_run_at": None,
        "last_error": None,
    }

    all_healthy = all(checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": __version__,
        "environment": settings.app_env,
        "checks": checks,
        "scheduler": scheduler_status,
        "timestamp": datetime.now(UTC),
    }


@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"status": "ok", "message": "pong"}


@router.get("/system", response_model=SystemInfoResponse)
async def system_info(
    current_user: User = Depends(get_current_user_optional),
):
    """
    Get system information
    Shows feature flags and policy status
    """
    settings = get_settings()
    get_policy_engine()

    # Feature flags
    features = {
        "provider_gateway": settings.feature_provider_gateway,
        "network_gateway": settings.feature_network_gateway,
        "browser_gateway": settings.feature_browser_gateway,
        "external_tools": settings.feature_external_tools,
    }

    # Policy status
    policies = {
        "default_deny": settings.policy_default_deny,
        "unknown_deny": settings.policy_unknown_deny,
        "fail_closed": True,  # Always true
    }

    return SystemInfoResponse(
        version=__version__,
        environment=settings.app_env,
        features=features,
        policies=policies,
    )

