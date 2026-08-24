"""
RBAC (Role-Based Access Control)
Extended implementation for Stage 2 with flexible permissions
"""

from enum import Enum
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import PermissionDeniedError
from src.identity.models import RoleEnum, User

logger = structlog.get_logger(__name__)


class Permission(str, Enum):
    """System permissions"""

    # System
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIGURE = "system:configure"

    # Users
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_GRANT_ADMIN = "user:grant_admin"
    USER_UPDATE_ROLE = "user:update_role"
    USER_DISABLE = "user:disable"

    # Roles
    ROLE_READ = "role:read"
    ROLE_WRITE = "role:write"
    ROLE_DELETE = "role:delete"

    # Permissions
    PERMISSION_READ = "permission:read"
    PERMISSION_GRANT = "permission:grant"

    # Audit
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Approval
    APPROVAL_READ = "approval:read"
    APPROVAL_CREATE = "approval:create"
    APPROVAL_APPROVE = "approval:approve"
    APPROVAL_REJECT = "approval:reject"

    # Policy
    POLICY_READ = "policy:read"
    POLICY_WRITE = "policy:write"

    # Knowledge
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_DELETE = "knowledge:delete"

    # AI Brain (Phase 3.1)
    AI_BRAIN_COMMAND_EXECUTE = "ai_brain:command:execute"
    AI_BRAIN_PLAN_READ = "ai_brain:plan:read"
    AI_BRAIN_TASK_READ = "ai_brain:task:read"

    # Task System
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_EXECUTE = "task:execute"
    TASK_ASSIGN = "task:assign"

    # Workflow System
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_UPDATE = "workflow:update"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_EXECUTE = "workflow:execute"

    # AI Agent System (Stage 3)
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"

    # AI Workforce System (Stage 6)
    WORKFORCE_CREATE = "workforce:create"
    WORKFORCE_READ = "workforce:read"
    WORKFORCE_UPDATE = "workforce:update"
    WORKFORCE_DELETE = "workforce:delete"
    EMPLOYEE_CREATE = "employee:create"
    EMPLOYEE_READ = "employee:read"
    EMPLOYEE_UPDATE = "employee:update"
    EMPLOYEE_DELETE = "employee:delete"
    EMPLOYEE_ACTIVATE = "employee:activate"
    EMPLOYEE_SUSPEND = "employee:suspend"
    EMPLOYEE_RETIRE = "employee:retire"
    EMPLOYEE_PERFORMANCE_READ = "employee:performance_read"
    EMPLOYEE_COST_READ = "employee:cost_read"

    # Business OS System (Stage 7)
    BUSINESS_CREATE = "business:create"
    BUSINESS_READ = "business:read"
    BUSINESS_UPDATE = "business:update"
    BUSINESS_DELETE = "business:delete"
    BUSINESS_EXECUTE = "business:execute"
    BUSINESS_TASK_CREATE = "business_task:create"
    BUSINESS_TASK_READ = "business_task:read"
    BUSINESS_TASK_UPDATE = "business_task:update"
    BUSINESS_TASK_DELETE = "business_task:delete"
    BUSINESS_METRICS_READ = "business_metrics:read"

    # Supplier Management (Week 7)
    SUPPLIER_CREATE = "supplier:create"
    SUPPLIER_READ = "supplier:read"
    SUPPLIER_UPDATE = "supplier:update"
    SUPPLIER_DELETE = "supplier:delete"

    # CEO AI OS System (Stage 8)
    CEO_COMMAND_EXECUTE = "ceo:command_execute"
    CEO_ANALYTICS_READ = "ceo:analytics_read"
    CEO_SYSTEM_CONTROL = "ceo:system_control"
    CEO_WORKFORCE_MANAGE = "ceo:workforce_manage"

    # CEO Dashboard
    CEO_DASHBOARD_READ = "ceo_dashboard:read"


# All available permissions
PERMISSIONS = list(Permission)

# Role-Permission mapping
ROLE_PERMISSIONS = {
    RoleEnum.ADMIN: [
        Permission.SYSTEM_READ,
        Permission.SYSTEM_WRITE,
        Permission.SYSTEM_ADMIN,
        Permission.SYSTEM_CONFIGURE,
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.USER_GRANT_ADMIN,
        Permission.USER_UPDATE_ROLE,
        Permission.USER_DISABLE,
        Permission.ROLE_READ,
        Permission.ROLE_WRITE,
        Permission.ROLE_DELETE,
        Permission.PERMISSION_READ,
        Permission.PERMISSION_GRANT,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.APPROVAL_READ,
        Permission.APPROVAL_CREATE,
        Permission.APPROVAL_APPROVE,
        Permission.APPROVAL_REJECT,
        Permission.POLICY_READ,
        Permission.POLICY_WRITE,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_WRITE,
        Permission.KNOWLEDGE_DELETE,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_DELETE,
        Permission.TASK_EXECUTE,
        Permission.TASK_ASSIGN,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_UPDATE,
        Permission.WORKFLOW_DELETE,
        Permission.WORKFLOW_EXECUTE,
        # Stage 3 - AI Agent
        Permission.AGENT_CREATE,
        Permission.AGENT_READ,
        Permission.AGENT_UPDATE,
        Permission.AGENT_DELETE,
        Permission.AGENT_EXECUTE,
        # Stage 6 - AI Workforce
        Permission.WORKFORCE_CREATE,
        Permission.WORKFORCE_READ,
        Permission.WORKFORCE_UPDATE,
        Permission.WORKFORCE_DELETE,
        Permission.EMPLOYEE_CREATE,
        Permission.EMPLOYEE_READ,
        Permission.EMPLOYEE_UPDATE,
        Permission.EMPLOYEE_DELETE,
        Permission.EMPLOYEE_ACTIVATE,
        Permission.EMPLOYEE_SUSPEND,
        Permission.EMPLOYEE_RETIRE,
        Permission.EMPLOYEE_PERFORMANCE_READ,
        Permission.EMPLOYEE_COST_READ,
        # Stage 7 - Business OS
        Permission.BUSINESS_CREATE,
        Permission.BUSINESS_READ,
        Permission.BUSINESS_UPDATE,
        Permission.BUSINESS_DELETE,
        Permission.BUSINESS_EXECUTE,
        Permission.BUSINESS_TASK_CREATE,
        Permission.BUSINESS_TASK_READ,
        Permission.BUSINESS_TASK_UPDATE,
        Permission.BUSINESS_TASK_DELETE,
        Permission.BUSINESS_METRICS_READ,
        # Week 7 - Supplier Management
        Permission.SUPPLIER_CREATE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_UPDATE,
        Permission.SUPPLIER_DELETE,
        # Stage 8 - CEO AI OS
        Permission.CEO_COMMAND_EXECUTE,
        Permission.CEO_ANALYTICS_READ,
        Permission.CEO_SYSTEM_CONTROL,
        Permission.CEO_WORKFORCE_MANAGE,
        Permission.CEO_DASHBOARD_READ,
        # Phase 3.1 - AI Brain
        Permission.AI_BRAIN_COMMAND_EXECUTE,
        Permission.AI_BRAIN_PLAN_READ,
        Permission.AI_BRAIN_TASK_READ,
    ],
    RoleEnum.USER: [
        Permission.SYSTEM_READ,
        Permission.USER_READ,
        Permission.ROLE_READ,
        Permission.PERMISSION_READ,
        Permission.AUDIT_READ,
        Permission.APPROVAL_READ,
        Permission.APPROVAL_CREATE,
        Permission.POLICY_READ,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_WRITE,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_EXECUTE,
        Permission.TASK_ASSIGN,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        # Stage 3 - AI Agent (limited)
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        # Stage 6 - AI Workforce (limited)
        Permission.WORKFORCE_READ,
        Permission.EMPLOYEE_READ,
        Permission.EMPLOYEE_PERFORMANCE_READ,
        # Stage 7 - Business OS (operational)
        Permission.BUSINESS_CREATE,
        Permission.BUSINESS_READ,
        Permission.BUSINESS_UPDATE,
        Permission.BUSINESS_EXECUTE,
        Permission.BUSINESS_TASK_CREATE,
        Permission.BUSINESS_TASK_READ,
        Permission.BUSINESS_TASK_UPDATE,
        Permission.BUSINESS_METRICS_READ,
        # Week 7 - Supplier Management
        Permission.SUPPLIER_CREATE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_UPDATE,
        Permission.SUPPLIER_DELETE,
        # Phase 3.1 - AI Brain (operational)
        Permission.AI_BRAIN_PLAN_READ,
        Permission.AI_BRAIN_TASK_READ,
    ],
    RoleEnum.VIEWER: [
        Permission.SYSTEM_READ,
        Permission.ROLE_READ,
        Permission.PERMISSION_READ,
        Permission.AUDIT_READ,
        Permission.APPROVAL_READ,
        Permission.KNOWLEDGE_READ,
        Permission.TASK_READ,
        Permission.WORKFLOW_READ,
        # Stage 3 - AI Agent (read-only)
        Permission.AGENT_READ,
        # Stage 6 - AI Workforce (read-only)
        Permission.WORKFORCE_READ,
        Permission.EMPLOYEE_READ,
        Permission.EMPLOYEE_PERFORMANCE_READ,
        # Stage 7 - Business OS (read-only)
        Permission.BUSINESS_READ,
        Permission.BUSINESS_TASK_READ,
        Permission.BUSINESS_METRICS_READ,
        # Week 7 - Supplier Management (read-only)
        Permission.SUPPLIER_READ,
        # Stage 8 - CEO Dashboard (read-only)
        Permission.CEO_DASHBOARD_READ,
        # Phase 3.1 - AI Brain (read-only)
        Permission.AI_BRAIN_PLAN_READ,
    ],
}


def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if user has a specific permission

    Args:
        user: User object
        permission: Required permission

    Returns:
        True if user has permission, False otherwise
    """
    if not user.is_active:
        logger.warning("permission_check_inactive_user", user_id=user.id)
        return False

    # Superuser has all permissions
    if user.is_superuser:
        return True

    # Check role permissions
    role_perms = ROLE_PERMISSIONS.get(user.role, [])
    has_perm = permission in role_perms

    logger.info(
        "permission_check",
        user_id=user.id,
        role=user.role,
        permission=permission,
        result=has_perm,
    )

    return has_perm


def require_permission(user: Optional[User], permission: Permission) -> None:
    """
    Require user to have a specific permission

    Args:
        user: User object (None = no user)
        permission: Required permission

    Raises:
        PermissionDeniedError: If user doesn't have permission (Fail Closed)
    """
    if user is None:
        logger.warning("permission_denied_no_user", permission=permission)
        raise PermissionDeniedError(f"Authentication required for: {permission}")

    if not has_permission(user, permission):
        logger.warning(
            "permission_denied",
            user_id=user.id,
            role=user.role,
            permission=permission,
        )
        raise PermissionDeniedError(f"Insufficient permissions. Required: {permission}")

    logger.info(
        "permission_granted",
        user_id=user.id,
        permission=permission,
    )


def is_admin(user: User) -> bool:
    """Check if user is admin"""
    return user.is_superuser or user.role == RoleEnum.ADMIN


def require_admin(user: Optional[User]) -> None:
    """
    Require user to be admin

    Raises:
        PermissionDeniedError: If user is not admin (Fail Closed)
    """
    if user is None:
        raise PermissionDeniedError("Admin authentication required")

    if not is_admin(user):
        logger.warning("admin_required", user_id=user.id, role=user.role)
        raise PermissionDeniedError("Admin privileges required")


class RBACService:
    """
    Extended RBAC Service for Stage 2

    Provides flexible role and permission management with database support.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("rbac_service_initialized")

    async def check_permission(
        self,
        user: User,
        resource: str,
        action: str,
        scope: Optional[str] = None,
    ) -> bool:
        """
        Check if user has permission for resource:action:scope

        Falls back to enum-based permissions if database roles not found.
        """
        if not user.is_active:
            logger.warning("permission_check_inactive_user", user_id=user.id)
            return False

        # Superuser bypass
        if user.is_superuser:
            return True

        # Build permission code
        perm_code = f"{resource}:{action}"
        if scope:
            perm_code += f":{scope}"

        # Try enum-based permission first (backward compatibility)
        try:
            perm_enum = Permission(perm_code)
            if has_permission(user, perm_enum):
                return True
        except ValueError:
            pass

        # Check database-based permissions
        # For Stage 2, we rely on enum-based permissions
        # Full database RBAC can be extended in future

        logger.debug(
            "permission_check_failed",
            user_id=user.id,
            permission=perm_code,
        )
        return False

    async def check_permission_by_id(
        self,
        user_id,
        permission_enum: Permission,
    ) -> bool:
        """
        Convenience method for checking permission by user_id + Permission enum.

        Args:
            user_id: User ID (UUID or int)
            permission_enum: Permission enum (e.g., Permission.TASK_CREATE)

        Returns:
            bool: Whether user has permission
        """
        # Parse permission enum into resource:action:scope
        parts = permission_enum.value.split(":")
        if len(parts) == 2:
            resource, action, scope = parts[0], parts[1], None
        elif len(parts) == 3:
            resource, action, scope = parts[0], parts[1], parts[2]
        else:
            logger.error("invalid_permission_format", permission=permission_enum.value)
            return False

        # Query user from database
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("permission_check_user_not_found", user_id=user_id)
            return False

        return await self.check_permission(user, resource, action, scope)

    async def require_permission_async(
        self,
        user: Optional[User],
        resource: str,
        action: str,
        scope: Optional[str] = None,
    ) -> None:
        """
        Async version of require_permission

        Raises:
            PermissionDeniedError: If user lacks permission (Fail Closed)
        """
        if user is None:
            perm_code = f"{resource}:{action}"
            if scope:
                perm_code += f":{scope}"
            logger.warning("permission_denied_no_user", permission=perm_code)
            raise PermissionDeniedError(f"Authentication required for: {perm_code}")

        has_perm = await self.check_permission(user, resource, action, scope)
        if not has_perm:
            perm_code = f"{resource}:{action}"
            if scope:
                perm_code += f":{scope}"
            logger.warning(
                "permission_denied",
                user_id=user.id,
                role=user.role,
                permission=perm_code,
            )
            raise PermissionDeniedError(f"Insufficient permissions. Required: {perm_code}")

    async def get_user_permissions(self, user: User) -> list[str]:
        """
        Get all permissions for a user

        Returns:
            List of permission codes (e.g., ['users:read', 'users:write'])
        """
        if not user.is_active:
            return []

        # Superuser has all permissions
        if user.is_superuser:
            return [p.value for p in Permission]

        # Get permissions from role
        role_perms = ROLE_PERMISSIONS.get(user.role, [])
        return [p.value for p in role_perms]
