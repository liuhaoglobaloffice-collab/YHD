"""
Audit logging service
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.models import AuditLog

logger = structlog.get_logger(__name__)


class AuditAction(str, Enum):
    """Standard audit action types"""

    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # Authorization
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHECK = "permission_check"

    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_DISABLED = "user_disabled"
    USER_ENABLED = "user_enabled"
    ROLE_CHANGED = "role_changed"

    # Session management
    SESSION_CREATED = "session_created"
    SESSION_REVOKED = "session_revoked"
    SESSION_EXPIRED = "session_expired"

    # Approval workflow
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_CANCELLED = "approval_cancelled"

    # Knowledge operations
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_INDEXED = "document_indexed"
    DOCUMENT_SEARCHED = "document_searched"
    KNOWLEDGE_RETRIEVED = "knowledge_retrieved"

    # Memory operations
    MEMORY_STORED = "memory_stored"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_EXPIRED = "memory_expired"

    # Task operations
    TASK_CREATED = "task_created"
    TASK_READ = "task_read"
    TASK_LIST = "task_list"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Workflow operations
    WORKFLOW_CREATE = "workflow_create"
    WORKFLOW_READ = "workflow_read"
    WORKFLOW_LIST = "workflow_list"
    WORKFLOW_UPDATE = "workflow_update"
    WORKFLOW_DELETE = "workflow_delete"
    WORKFLOW_EXECUTE = "workflow_execute"
    WORKFLOW_PAUSE = "workflow_pause"
    WORKFLOW_RESUME = "workflow_resume"
    WORKFLOW_CANCEL = "workflow_cancel"

    # AI Agent operations (Stage 3)
    AGENT_CREATED = "agent_created"
    AGENT_READ = "agent_read"
    AGENT_UPDATED = "agent_updated"
    AGENT_DELETED = "agent_deleted"
    AGENT_EXECUTED = "agent_executed"
    AGENT_FAILED = "agent_failed"

    # AI Workforce operations (Stage 6)
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_READ = "employee_read"
    EMPLOYEE_LIST = "employee_list"
    EMPLOYEE_UPDATED = "employee_updated"
    EMPLOYEE_DELETED = "employee_deleted"
    EMPLOYEE_ACTIVATED = "employee_activated"
    EMPLOYEE_SUSPENDED = "employee_suspended"
    EMPLOYEE_RETIRED = "employee_retired"
    EMPLOYEE_ASSIGNED = "employee_assigned"
    EMPLOYEE_PERFORMANCE_READ = "employee_performance_read"
    EMPLOYEE_COST_READ = "employee_cost_read"

    # Business OS operations (Stage 7)
    BUSINESS_TASK_CREATED = "business_task_created"
    BUSINESS_TASK_READ = "business_task_read"
    BUSINESS_TASK_LIST = "business_task_list"
    BUSINESS_TASK_UPDATED = "business_task_updated"
    BUSINESS_TASK_DELETED = "business_task_deleted"
    BUSINESS_TASK_ASSIGNED = "business_task_assigned"
    BUSINESS_TASK_COMPLETED = "business_task_completed"
    BUSINESS_TASK_FAILED = "business_task_failed"
    BUSINESS_METRICS_READ = "business_metrics_read"

    # Supplier Intelligence operations (Module 48)
    SUPPLIER_CREATED = "supplier_created"
    SUPPLIER_UPDATED = "supplier_updated"
    SUPPLIER_DELETED = "supplier_deleted"
    SUPPLIER_READ = "supplier_read"

    # CEO AI OS operations (Stage 8)
    CEO_COMMAND_EXECUTED = "ceo_command_executed"
    CEO_COMMAND_FAILED = "ceo_command_failed"
    CEO_ANALYTICS_READ = "ceo_analytics_read"
    CEO_SYSTEM_CONTROL = "ceo_system_control"
    CEO_DASHBOARD_READ = "ceo_dashboard_read"

    # AI Brain operations (Phase 3.1)
    AI_BRAIN_COMMAND_CREATED = "ai_brain_command_created"
    AI_BRAIN_COMMAND_EXECUTED = "ai_brain_command_executed"
    AI_BRAIN_COMMAND_FAILED = "ai_brain_command_failed"
    AI_BRAIN_COMMAND_CANCELLED = "ai_brain_command_cancelled"
    AI_BRAIN_PLAN_READ = "ai_brain_plan_read"
    AI_BRAIN_TASK_ROUTED = "ai_brain_task_routed"

    # Policy and security
    POLICY_EVALUATED = "policy_evaluated"
    POLICY_VIOLATED = "policy_violated"
    SECURITY_BREACH = "security_breach"

    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGED = "configuration_changed"


class AuditService:
    """
    Audit logging service for critical operations
    All audit logs are persisted to database
    """

    # Sensitive field names to redact from audit logs
    SENSITIVE_FIELDS = {
        "password",
        "hashed_password",
        "secret",
        "token",
        "api_key",
        "access_token",
        "refresh_token",
        "jwt",
        "bearer",
        "authorization",
        "private_key",
        "secret_key",
        "credential",
        "credentials",
    }

    # Patterns that indicate a value is likely a secret
    SECRET_VALUE_PATTERNS = [
        "sk-",  # OpenAI/Stripe test keys
        "sk_live_",  # Stripe live keys
        "sk_test_",  # Stripe test keys
        "rk_live_",  # Stripe restricted keys
        "pk_live_",  # Stripe publishable keys
        "Bearer ",  # Bearer tokens
    ]

    @staticmethod
    def _sanitize_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sanitize sensitive data from audit log details
        Redacts passwords, tokens, secrets, etc.
        """
        if not details:
            return {}

        sanitized = {}
        for key, value in details.items():
            if isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = AuditService._sanitize_details(value)
            elif isinstance(value, list):
                # Sanitize list items if they are dicts
                sanitized[key] = [
                    AuditService._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Check if key contains sensitive field name
                key_lower = key.lower()
                is_sensitive = any(sens in key_lower for sens in AuditService.SENSITIVE_FIELDS)

                # Also check if value looks like a secret (API key pattern)
                if not is_sensitive and isinstance(value, str):
                    is_sensitive = any(
                        value.startswith(pattern) for pattern in AuditService.SECRET_VALUE_PATTERNS
                    )

                sanitized[key] = "[REDACTED]" if is_sensitive else value

        return sanitized

    @staticmethod
    async def log(
        session: AsyncSession,
        action: str | AuditAction,
        resource_type: str,
        status: str,
        user_id: Optional[int | str] = None,
        resource_id: Optional[str | Any] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create audit log entry

        Args:
            session: Database session
            action: Action performed (e.g., "login", "create_user")
            resource_type: Type of resource (e.g., "user", "policy")
            status: Result status ("success", "failure", "denied")
            user_id: User who performed the action
            resource_id: ID of affected resource
            details: Additional details (no secrets!)
            error_message: Error message if failed
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created AuditLog object
        """
        # Sanitize details to remove secrets
        sanitized_details = AuditService._sanitize_details(details)

        # Convert enum to string if needed
        action_str = action.value if isinstance(action, AuditAction) else action

        # Convert UUID to string for SQLite compatibility
        from uuid import UUID

        if isinstance(user_id, UUID):
            user_id = str(user_id)
        if isinstance(resource_id, UUID):
            resource_id = str(resource_id)

        audit_log = AuditLog(
            user_id=user_id,
            action=action_str,
            resource_type=resource_type,
            resource_id=resource_id,
            details=sanitized_details,
            status=status,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(UTC),
        )

        session.add(audit_log)
        await session.commit()
        await session.refresh(audit_log)

        logger.info(
            "audit_log_created",
            audit_id=audit_log.id,
            action=action_str,
            resource_type=resource_type,
            status=status,
            user_id=user_id,
        )

        return audit_log

    @staticmethod
    async def log_success(
        session: AsyncSession,
        action: str,
        resource_type: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log successful operation"""
        return await AuditService.log(
            session=session,
            action=action,
            resource_type=resource_type,
            status="success",
            user_id=user_id,
            resource_id=resource_id,
            details=details,
        )

    @staticmethod
    async def log_failure(
        session: AsyncSession,
        action: str,
        resource_type: str,
        error_message: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log failed operation"""
        return await AuditService.log(
            session=session,
            action=action,
            resource_type=resource_type,
            status="failure",
            user_id=user_id,
            resource_id=resource_id,
            details=details,
            error_message=error_message,
        )

    @staticmethod
    async def log_denied(
        session: AsyncSession,
        action: str,
        resource_type: str,
        reason: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log denied operation (security/permission)"""
        return await AuditService.log(
            session=session,
            action=action,
            resource_type=resource_type,
            status="denied",
            user_id=user_id,
            resource_id=resource_id,
            details=details,
            error_message=reason,
        )

    @staticmethod
    async def log_login(
        session: AsyncSession,
        user_id: int,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Log user login attempt"""
        return await AuditService.log(
            session=session,
            action="login",
            resource_type="user",
            status="success" if success else "failure",
            user_id=user_id,
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
        )

    @staticmethod
    async def log_logout(
        session: AsyncSession,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log user logout"""
        return await AuditService.log(
            session=session,
            action="logout",
            resource_type="user",
            status="success",
            user_id=user_id,
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_permission_denied(
        session: AsyncSession,
        user_id: int,
        action: str,
        resource_type: str,
        reason: str,
        resource_id: Optional[str] = None,
    ) -> AuditLog:
        """Log permission denied"""
        return await AuditService.log(
            session=session,
            action=action,
            resource_type=resource_type,
            status="denied",
            user_id=user_id,
            resource_id=resource_id,
            error_message=reason,
        )

    @staticmethod
    async def log_role_change(
        session: AsyncSession,
        actor_id: int,
        target_user_id: int,
        old_role: str,
        new_role: str,
    ) -> AuditLog:
        """Log role change"""
        return await AuditService.log(
            session=session,
            action="change_role",
            resource_type="user",
            status="success",
            user_id=actor_id,
            resource_id=str(target_user_id),
            details={"old_role": old_role, "new_role": new_role},
        )

    @staticmethod
    async def log_approval(
        session: AsyncSession,
        approver_id: int,
        request_id: int,
        action: str,
        decision: str,
    ) -> AuditLog:
        """Log approval decision"""
        return await AuditService.log(
            session=session,
            action=f"approval_{action}",
            resource_type="approval_request",
            status="success",
            user_id=approver_id,
            resource_id=str(request_id),
            details={"decision": decision},
        )

    @staticmethod
    async def log_session_revoked(
        session: AsyncSession,
        actor_id: int,
        target_user_id: int,
        session_count: int,
    ) -> AuditLog:
        """Log session revocation"""
        return await AuditService.log(
            session=session,
            action="revoke_sessions",
            resource_type="session",
            status="success",
            user_id=actor_id,
            resource_id=str(target_user_id),
            details={"session_count": session_count},
        )

    @staticmethod
    async def query_logs(
        session: AsyncSession,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Query audit logs with filters
        """
        query = select(AuditLog)

        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if status:
            query = query.where(AuditLog.status == status)

        query = query.order_by(desc(AuditLog.timestamp)).limit(limit).offset(offset)

        result = await session.execute(query)
        return list(result.scalars().all())
