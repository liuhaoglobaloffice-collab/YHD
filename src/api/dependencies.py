"""
FastAPI dependencies for authentication and authorization
"""

from typing import Optional

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.registry import BusinessTaskRegistry
from src.business.service import BusinessService
from src.ceo.dashboard import get_ceo_dashboard
from src.core.errors import AuthenticationError
from src.identity.audit import AuditService
from src.identity.auth import decode_access_token
from src.identity.database import get_db_session
from src.identity.models import User
from src.identity.rbac import Permission, RBACService, has_permission
from src.workforce.cost import CostTracker
from src.workforce.employee import AIEmployeeService
from src.workforce.lifecycle import EmployeeLifecycleManager
from src.workforce.performance import PerformanceTracker
from src.workforce.registry import AIEmployeeRegistry

logger = structlog.get_logger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Get current authenticated user from JWT token.

    Keep the existing dependency and auth stack intact while accepting the
    token payload contract already produced by the app: `sub` stores the
    user id string, not necessarily the username.

    Raises:
        HTTPException: If authentication fails
    """
    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        if not subject:
            raise AuthenticationError("Invalid token payload")

        # Most of the repo emits `sub` as a user id string when generating a
        # token from the login route. Support both the integer-id and username
        # lookup patterns to stay compatible with the project’s existing tests.
        user = None
        try:
            user_id = int(str(subject))
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
        except Exception:
            result = await session.execute(select(User).where(User.username == subject))
            user = result.scalar_one_or_none()

        if user is None:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User is inactive")

        return user

    except AuthenticationError as e:
        logger.warning("authentication_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    session: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current user, but return None if not authenticated (for optional auth)
    """
    if credentials is None:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str = payload.get("sub")
        user_id: int = int(user_id_str) if user_id_str else None

        if user_id is None:
            return None

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user and user.is_active:
            return user

        return None

    except Exception:
        return None


def require_permission_dependency(permission: Permission):
    """
    Create a dependency that requires a specific permission

    Usage:
        @app.get("/admin", dependencies=[Depends(require_permission_dependency(Permission.SYSTEM_ADMIN))])
    """

    async def _check_permission(
        current_user: User = Depends(get_current_user),
    ):
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}",
            )
        return current_user

    return _check_permission


# Alias for backward compatibility
require_permission = require_permission_dependency


# Stage 6: Workforce service dependencies
_employee_registry = None
_employee_service = None
_lifecycle_manager = None
_performance_tracker = None
_cost_tracker = None

# Stage 7: Business service dependencies
_business_service = None


def get_employee_registry(
    session: AsyncSession = Depends(get_db_session),
) -> AIEmployeeRegistry:
    """Get AI Employee Registry singleton."""
    global _employee_registry
    if _employee_registry is None:
        _employee_registry = AIEmployeeRegistry(session)
    return _employee_registry


def get_employee_service(
    registry: AIEmployeeRegistry = Depends(get_employee_registry),
) -> AIEmployeeService:
    """Get AI Employee Service."""
    global _employee_service
    if _employee_service is None:
        from src.core.di import get_container

        container = get_container()
        rbac_service = container.get(RBACService)
        audit_service = container.get(AuditService)
        _employee_service = AIEmployeeService(registry, rbac_service, audit_service)
    return _employee_service


def get_lifecycle_manager(
    registry: AIEmployeeRegistry = Depends(get_employee_registry),
) -> EmployeeLifecycleManager:
    """Get Employee Lifecycle Manager."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        from src.core.di import get_container

        container = get_container()
        rbac_service = container.get(RBACService)
        audit_service = container.get(AuditService)
        _lifecycle_manager = EmployeeLifecycleManager(registry, rbac_service, audit_service)
    return _lifecycle_manager


def get_performance_tracker(
    registry: AIEmployeeRegistry = Depends(get_employee_registry),
) -> PerformanceTracker:
    """Get Performance Tracker."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker(registry)
    return _performance_tracker


def get_cost_tracker(
    registry: AIEmployeeRegistry = Depends(get_employee_registry),
) -> CostTracker:
    """Get Cost Tracker."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker(registry)
    return _cost_tracker


async def get_business_task_registry(
    session: AsyncSession = Depends(get_db_session),
) -> BusinessTaskRegistry:
    """Get Business Task Registry."""
    return BusinessTaskRegistry(session=session)


def get_business_service(
    task_registry: BusinessTaskRegistry = Depends(get_business_task_registry),
    employee_registry: AIEmployeeRegistry = Depends(get_employee_registry),
) -> BusinessService:
    """Get Business Service."""
    global _business_service
    if _business_service is None:
        from src.core.di import get_container

        container = get_container()
        rbac_service = container.get(RBACService)
        audit_service = container.get(AuditService)
        _business_service = BusinessService(
            task_registry, employee_registry, rbac_service, audit_service
        )
    return _business_service

    # def get_ceo_dashboard_dep(...) - Defined in ceo.py routes -> CEODashboard:
    """Get CEO Dashboard."""
    return get_ceo_dashboard(
        business_registry=business_registry,
        employee_registry=employee_registry,
        approval_service=approval_service,
        audit_service=audit_service,
        rbac_service=rbac_service,
    )
