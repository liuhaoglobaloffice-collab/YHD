"""
Health check and system info endpoints
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends

from src import __version__
from src.api.dependencies import get_current_user_optional
from src.api.schemas import HealthResponse, SystemInfoResponse
from src.core.config import get_settings
from src.core.lifecycle import get_lifecycle_manager
from src.identity.models import User
from src.security.policy import get_policy_engine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns system status
    """
    settings = get_settings()
    lifecycle = get_lifecycle_manager()

    status = "healthy" if lifecycle.is_ready() else "unhealthy"

    logger.info("health_check", status=status)

    return HealthResponse(
        status=status,
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
    )


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
