"""
Approval Dependencies for FastAPI
Provides dependency injection for approval workflow
"""

from typing import Optional

import structlog
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.governance.approval import ApprovalService
from src.identity.models import ApprovalRequest, User

logger = structlog.get_logger(__name__)


async def get_approval_service(
    session: AsyncSession = Depends(get_db),
) -> ApprovalService:
    """Get ApprovalService instance"""
    return ApprovalService(session)


async def require_approval(
    resource: str,
    action: str,
    resource_id: Optional[str] = None,
    context: Optional[dict] = None,
) -> Optional[ApprovalRequest]:
    """
    Dependency to check if operation requires approval

    Usage:
        @router.delete("/tasks/{task_id}")
        async def delete_task(
            task_id: UUID,
            approval: Optional[ApprovalRequest] = Depends(
                require_approval_for("task", "delete")
            ),
        ):
            if approval and approval.status != "approved":
                raise HTTPException(403, "Approval required")
            # Execute operation

    Args:
        resource: Resource type (e.g., "task", "workflow")
        action: Action type (e.g., "delete", "execute")
        resource_id: Optional resource ID
        context: Optional context for risk evaluation

    Returns:
        ApprovalRequest if approval required and found, None if auto-approved

    Raises:
        HTTPException 403: If approval required but not found or not approved
    """

    async def _check_approval(
        session: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        approval_service: ApprovalService = Depends(get_approval_service),
    ) -> Optional[ApprovalRequest]:
        """Inner dependency that accesses session and user"""

        # Check if operation requires approval
        can_auto_approve = await approval_service.check_auto_approval(
            requester=current_user,
            request_type="operation",
            target_resource=resource,
            target_action=action,
            context=context or {},
        )

        if can_auto_approve:
            logger.info(
                "operation_auto_approved",
                user_id=current_user.id,
                resource=resource,
                action=action,
            )
            return None

        # Approval required - check if exists
        # For now, we create approval request automatically
        # In production, client should create approval first
        logger.warning(
            "approval_required",
            user_id=current_user.id,
            resource=resource,
            action=action,
            resource_id=resource_id,
        )

        raise HTTPException(
            status_code=403,
            detail={
                "error": "approval_required",
                "message": f"Operation {resource}:{action} requires approval",
                "resource": resource,
                "action": action,
                "resource_id": resource_id,
            },
        )

    return _check_approval


def require_approval_for(resource: str, action: str, context: Optional[dict] = None):
    """
    Factory function to create approval dependency

    Usage:
        @router.delete("/tasks/{task_id}")
        async def delete_task(
            task_id: UUID,
            _: None = Depends(require_approval_for("task", "delete")),
        ):
            # If we reach here, approval is not required or already approved
            # Execute operation
    """

    async def _check(
        session: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> None:
        """Check if approval required"""
        approval_service = ApprovalService(session)

        # Check if operation can be auto-approved
        can_auto_approve = await approval_service.check_auto_approval(
            requester=current_user,
            request_type="operation",
            target_resource=resource,
            target_action=action,
            context=context or {},
        )

        if can_auto_approve:
            logger.info(
                "operation_auto_approved",
                user_id=current_user.id,
                resource=resource,
                action=action,
            )
            return None

        # High-risk operation requires approval
        logger.warning(
            "approval_required_blocking",
            user_id=current_user.id,
            resource=resource,
            action=action,
        )

        raise HTTPException(
            status_code=403,
            detail={
                "error": "approval_required",
                "message": f"Operation {resource}:{action} requires admin approval. Please request approval first.",
                "resource": resource,
                "action": action,
                "instruction": f"POST /api/v1/approvals/requests with resource={resource}, action={action}",
            },
        )

    return _check
