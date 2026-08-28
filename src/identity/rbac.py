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
from src.identity.models import AccountType, BusinessRole, RoleEnum, User

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

    # S1 - Data Import (操作台资料导入)
    IMPORT_CREATE = "import:create"
    IMPORT_READ = "import:read"

    # S2 - Multi-platform Integration (多平台接入)
    PLATFORM_CREATE = "platform:create"
    PLATFORM_READ = "platform:read"
    PLATFORM_DELETE = "platform:delete"
    PLATFORM_MESSAGE_SEND = "platform:message_send"

    # S3 - Acquisition & CRM (自动获客 + 供应商分析)
    LEAD_CREATE = "lead:create"
    LEAD_READ = "lead:read"
    LEAD_UPDATE = "lead:update"
    LEAD_DELETE = "lead:delete"
    CUSTOMS_READ = "customs:read"

    # S4 - Website & SEO (独立站 + SEO)
    SITE_CREATE = "site:create"
    SITE_READ = "site:read"
    SITE_UPDATE = "site:update"
    SITE_DELETE = "site:delete"
    SEO_READ = "seo:read"

    # CEO AI OS System (Stage 8)
    CEO_COMMAND_EXECUTE = "ceo:command_execute"
    CEO_ANALYTICS_READ = "ceo:analytics_read"
    CEO_SYSTEM_CONTROL = "ceo:system_control"
    CEO_WORKFORCE_MANAGE = "ceo:workforce_manage"

    # CEO Dashboard
    CEO_DASHBOARD_READ = "ceo_dashboard:read"

    # Quotation Management (P3f)
    QUOTE_CREATE = "quote:create"
    QUOTE_READ = "quote:read"
    QUOTE_UPDATE = "quote:update"
    QUOTE_DELETE = "quote:delete"
    QUOTE_SEND = "quote:send"


# All available permissions
PERMISSIONS = list(Permission)

# ==================== 业务角色权限预设 ====================
# 每个子账号分配一个业务角色，角色包含一组默认权限
# 主账号可在权限控制中心为每个子账号单独调整

BUSINESS_ROLE_PERMISSIONS: dict[BusinessRole, list[Permission]] = {
    BusinessRole.SALES: [  # 销售 - 客户开发、CRM、社媒营销
        Permission.USER_READ,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_EXECUTE,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.LEAD_CREATE,
        Permission.LEAD_READ,
        Permission.LEAD_UPDATE,
        Permission.LEAD_DELETE,
        Permission.PLATFORM_READ,
        Permission.PLATFORM_MESSAGE_SEND,
        Permission.IMPORT_CREATE,
        Permission.IMPORT_READ,
        Permission.BUSINESS_CREATE,
        Permission.BUSINESS_READ,
        Permission.BUSINESS_UPDATE,
        Permission.BUSINESS_EXECUTE,
        Permission.BUSINESS_TASK_CREATE,
        Permission.BUSINESS_TASK_READ,
        Permission.BUSINESS_TASK_UPDATE,
        Permission.BUSINESS_METRICS_READ,
        Permission.EMPLOYEE_READ,
        Permission.QUOTE_CREATE,
        Permission.QUOTE_READ,
        Permission.QUOTE_UPDATE,
        Permission.QUOTE_SEND,
    ],
    BusinessRole.PURCHASING: [  # 采购 - 供应商搜索、分析、采购谈判
        Permission.USER_READ,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_EXECUTE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.SUPPLIER_CREATE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_UPDATE,
        Permission.SUPPLIER_DELETE,
        Permission.CUSTOMS_READ,
        Permission.LEAD_READ,
        Permission.BUSINESS_CREATE,
        Permission.BUSINESS_READ,
        Permission.BUSINESS_UPDATE,
        Permission.BUSINESS_EXECUTE,
        Permission.BUSINESS_TASK_CREATE,
        Permission.BUSINESS_TASK_READ,
        Permission.BUSINESS_TASK_UPDATE,
        Permission.BUSINESS_METRICS_READ,
        Permission.QUOTE_READ,
        Permission.QUOTE_UPDATE,
    ],
    BusinessRole.OPERATIONS: [  # 运营 - 数据运营、SEO、独立站、内容发布
        Permission.USER_READ,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_EXECUTE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.SITE_CREATE,
        Permission.SITE_READ,
        Permission.SITE_UPDATE,
        Permission.SITE_DELETE,
        Permission.SEO_READ,
        Permission.BUSINESS_CREATE,
        Permission.BUSINESS_READ,
        Permission.BUSINESS_UPDATE,
        Permission.BUSINESS_EXECUTE,
        Permission.BUSINESS_TASK_CREATE,
        Permission.BUSINESS_TASK_READ,
        Permission.BUSINESS_TASK_UPDATE,
        Permission.BUSINESS_METRICS_READ,
        Permission.LEAD_READ,
        Permission.SUPPLIER_READ,
        Permission.CEO_DASHBOARD_READ,
        Permission.AUDIT_READ,
    ],
    BusinessRole.AI_ADMIN: [  # AI管理员 - 管理AI员工、技能、模型配置
        Permission.USER_READ,
        Permission.ROLE_READ,
        Permission.PERMISSION_READ,
        Permission.AUDIT_READ,
        Permission.APPROVAL_READ,
        Permission.APPROVAL_CREATE,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_EXECUTE,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.AGENT_CREATE,
        Permission.AGENT_READ,
        Permission.AGENT_UPDATE,
        Permission.AGENT_DELETE,
        Permission.AGENT_EXECUTE,
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
        Permission.EMPLOYEE_PERFORMANCE_READ,
        Permission.EMPLOYEE_COST_READ,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_WRITE,
        Permission.BUSINESS_READ,
        Permission.BUSINESS_METRICS_READ,
        Permission.CEO_DASHBOARD_READ,
        Permission.AI_BRAIN_COMMAND_EXECUTE,
        Permission.AI_BRAIN_PLAN_READ,
        Permission.AI_BRAIN_TASK_READ,
    ],
    BusinessRole.GENERAL: [  # 通用 - 多功能综合岗
        Permission.USER_READ,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_EXECUTE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.LEAD_CREATE,
        Permission.LEAD_READ,
        Permission.LEAD_UPDATE,
        Permission.SUPPLIER_CREATE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_UPDATE,
        Permission.CUSTOMS_READ,
        Permission.PLATFORM_READ,
        Permission.PLATFORM_MESSAGE_SEND,
        Permission.SITE_READ,
        Permission.SITE_UPDATE,
        Permission.SEO_READ,
        Permission.BUSINESS_CREATE,
        Permission.BUSINESS_READ,
        Permission.BUSINESS_UPDATE,
        Permission.BUSINESS_EXECUTE,
        Permission.BUSINESS_TASK_CREATE,
        Permission.BUSINESS_TASK_READ,
        Permission.BUSINESS_TASK_UPDATE,
        Permission.BUSINESS_METRICS_READ,
        Permission.EMPLOYEE_READ,
        Permission.QUOTE_CREATE,
        Permission.QUOTE_READ,
        Permission.QUOTE_UPDATE,
        Permission.CEO_DASHBOARD_READ,
    ],
}

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
        # S1 - Data Import
        Permission.IMPORT_CREATE,
        Permission.IMPORT_READ,
        # S2 - Multi-platform Integration
        Permission.PLATFORM_CREATE,
        Permission.PLATFORM_READ,
        Permission.PLATFORM_DELETE,
        Permission.PLATFORM_MESSAGE_SEND,
        # S3 - Acquisition & CRM
        Permission.LEAD_CREATE,
        Permission.LEAD_READ,
        Permission.LEAD_UPDATE,
        Permission.LEAD_DELETE,
        Permission.CUSTOMS_READ,
        # S4 - Website & SEO
        Permission.SITE_CREATE,
        Permission.SITE_READ,
        Permission.SITE_UPDATE,
        Permission.SITE_DELETE,
        Permission.SEO_READ,
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
        Permission.EMPLOYEE_CREATE,
        Permission.EMPLOYEE_READ,
        Permission.EMPLOYEE_UPDATE,
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
        # S1 - Data Import
        Permission.IMPORT_CREATE,
        Permission.IMPORT_READ,
        # S2 - Multi-platform Integration (operational)
        Permission.PLATFORM_CREATE,
        Permission.PLATFORM_READ,
        Permission.PLATFORM_DELETE,
        Permission.PLATFORM_MESSAGE_SEND,
        # S3 - Acquisition & CRM (operational)
        Permission.LEAD_CREATE,
        Permission.LEAD_READ,
        Permission.LEAD_UPDATE,
        Permission.LEAD_DELETE,
        Permission.CUSTOMS_READ,
        # S4 - Website & SEO (operational)
        Permission.SITE_CREATE,
        Permission.SITE_READ,
        Permission.SITE_UPDATE,
        Permission.SITE_DELETE,
        Permission.SEO_READ,
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
        # S1 - Data Import (read-only)
        Permission.IMPORT_READ,
        # S2 - Multi-platform Integration (read-only)
        Permission.PLATFORM_READ,
        # S3 - Acquisition & CRM (read-only)
        Permission.LEAD_READ,
        Permission.CUSTOMS_READ,
        # S4 - Website & SEO (read-only)
        Permission.SITE_READ,
        Permission.SEO_READ,
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

    # 主账号（OWNER）拥有所有操作权限
    if user.account_type == AccountType.OWNER:
        return True

    # 检查用户自定义权限配置（permissions_config 覆盖业务角色默认权限）
    perm_code = permission.value
    if user.permissions_config and perm_code in user.permissions_config:
        result = user.permissions_config[perm_code]
        logger.info(
            "permission_check_custom",
            user_id=user.id,
            permission=perm_code,
            result=result,
        )
        return result

    # 检查业务角色权限
    if user.business_role:
        role_perms = BUSINESS_ROLE_PERMISSIONS.get(user.business_role, [])
        if permission in role_perms:
            logger.info(
                "permission_check_business_role",
                user_id=user.id,
                business_role=user.business_role,
                permission=permission,
                result=True,
            )
            return True
        # 有业务角色但权限不在预设中 → 拒绝（不继续回退到系统角色）
        logger.info(
            "permission_check_business_role_denied",
            user_id=user.id,
            business_role=user.business_role,
            permission=permission,
            result=False,
        )
        return False

    # 检查系统角色权限（fallback，仅当无业务角色时）
    role_perms = ROLE_PERMISSIONS.get(user.role, [])
    has_perm = permission in role_perms

    logger.info(
        "permission_check",
        user_id=user.id,
        role=user.role,
        business_role=user.business_role,
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

        # 主账号拥有所有权限
        if user.account_type == AccountType.OWNER:
            return [p.value for p in Permission]

        # 从业务角色获取基础权限
        base_perms: set[str] = set()
        if user.business_role:
            role_perms = BUSINESS_ROLE_PERMISSIONS.get(user.business_role, [])
            base_perms = {p.value for p in role_perms}
        else:
            role_perms = ROLE_PERMISSIONS.get(user.role, [])
            base_perms = {p.value for p in role_perms}

        # 自定义权限配置覆盖业务角色/系统角色权限
        if user.permissions_config:
            for perm_code, enabled in user.permissions_config.items():
                if enabled:
                    base_perms.add(perm_code)
                else:
                    base_perms.discard(perm_code)

        return sorted(base_perms)
