"""
API Permission Dependencies
Phase 2F-3.2: Unified permission checking for FastAPI endpoints

Architecture:
    API Endpoint
        ↓ (Dependency)
    require_permission(resource, action)
        ↓
    RBACService.require_permission_async()
        ↓
    Permission Check (Fail Closed)
"""

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.core.errors import PermissionDeniedError
from src.identity.models import User
from src.identity.rbac import RBACService

logger = structlog.get_logger(__name__)


def require_permission(resource: str, action: str, scope: str = None):
    """
    FastAPI dependency for permission checking.

    Usage:
        @router.post("/tasks")
        async def create_task(
            ...,
            _: None = Depends(require_permission("task", "create")),
        ):
            # Permission already checked, proceed with business logic
            ...

    Args:
        resource: Resource type (e.g., "task", "workflow", "business")
        action: Action type (e.g., "create", "read", "update", "delete")
        scope: Optional scope (e.g., user_id, department)

    Returns:
        FastAPI dependency function

    Raises:
        PermissionDeniedError: If user lacks required permission (Fail Closed)
    """

    async def permission_checker(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> None:
        """
        Check if current user has required permission.

        Security First: All unknown permissions default DENY (Fail Closed).
        """
        if not current_user:
            logger.warning(
                "permission_denied_no_user",
                resource=resource,
                action=action,
                scope=scope,
            )
            raise PermissionDeniedError(f"Authentication required for {resource}:{action}")

        rbac = RBACService(session)

        try:
            await rbac.require_permission_async(
                user=current_user,
                resource=resource,
                action=action,
                scope=scope,
            )

            logger.debug(
                "permission_granted",
                user_id=current_user.id,
                resource=resource,
                action=action,
                scope=scope,
            )

        except PermissionDeniedError:
            logger.warning(
                "permission_denied",
                user_id=current_user.id,
                role=current_user.role,
                resource=resource,
                action=action,
                scope=scope,
            )
            raise

    return permission_checker


def require_any_permission(permissions: list[tuple[str, str]]):
    """
    Require at least one of multiple permissions (OR logic).

    Usage:
        @router.get("/dashboard")
        async def get_dashboard(
            ...,
            _: None = Depends(require_any_permission([
                ("ceo", "dashboard_read"),
                ("system", "admin"),
            ])),
        ):
            ...

    Args:
        permissions: List of (resource, action) tuples

    Returns:
        FastAPI dependency function

    Raises:
        PermissionDeniedError: If user lacks all permissions
    """

    async def permission_checker(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> None:
        if not current_user:
            raise PermissionDeniedError("Authentication required")

        rbac = RBACService(session)

        for resource, action in permissions:
            has_perm = await rbac.check_permission(
                user=current_user,
                resource=resource,
                action=action,
            )

            if has_perm:
                logger.debug(
                    "permission_granted_any",
                    user_id=current_user.id,
                    granted_permission=f"{resource}:{action}",
                )
                return

        logger.warning(
            "permission_denied_all",
            user_id=current_user.id,
            role=current_user.role,
            required_permissions=permissions,
        )

        raise PermissionDeniedError(f"Insufficient permissions. Required one of: {permissions}")

    return permission_checker


def require_admin():
    """
    Require admin role (ADMIN or superuser).

    Usage:
        @router.delete("/system/reset")
        async def reset_system(
            ...,
            _: None = Depends(require_admin()),
        ):
            ...

    Returns:
        FastAPI dependency function

    Raises:
        PermissionDeniedError: If user is not admin
    """

    async def admin_checker(
        current_user: User = Depends(get_current_user),
    ) -> None:
        if not current_user:
            raise PermissionDeniedError("Authentication required")

        from src.identity.rbac import is_admin

        if not is_admin(current_user):
            logger.warning(
                "admin_required",
                user_id=current_user.id,
                role=current_user.role,
            )
            raise PermissionDeniedError("Admin privileges required")

        logger.debug(
            "admin_access_granted",
            user_id=current_user.id,
        )

    return admin_checker
