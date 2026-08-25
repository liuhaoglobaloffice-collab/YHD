"""
Approval management API routes
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_permission
from src.api.schemas import (
    ApprovalDecision,
    ApprovalListResponse,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
)
from src.core.errors import PermissionDeniedError, ResourceNotFoundError, ValidationError
from src.governance.approval import ApprovalService
from src.identity.audit import AuditService
from src.identity.database import get_db_session
from src.identity.models import ApprovalRequest, ApprovalStatus, User

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalListResponse)
async def list_approval_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission("approval", "read")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List approval requests

    - Admin: see all requests
    - User: see only their own requests
    """
    query = select(ApprovalRequest)

    # Filter by status if provided
    if status_filter:
        try:
            status_enum = ApprovalStatus(status_filter.lower())
            query = query.where(ApprovalRequest.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    # Non-admin users can only see their own requests
    if current_user.role.value != "admin":
        query = query.where(ApprovalRequest.requester_id == current_user.id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    # Get requests
    query = query.offset(skip).limit(limit).order_by(ApprovalRequest.created_at.desc())
    result = await session.execute(query)
    requests = list(result.scalars().all())

    return ApprovalListResponse(
        requests=[ApprovalRequestResponse.model_validate(r) for r in requests],
        total=total,
    )


@router.get("/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    request_id: int,
    current_user: User = Depends(require_permission("approval", "read")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get approval request by ID
    """
    result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == request_id))
    approval_request = result.scalar_one_or_none()

    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found",
        )

    # Non-admin users can only see their own requests
    if current_user.role.value != "admin" and approval_request.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own approval requests",
        )

    return ApprovalRequestResponse.model_validate(approval_request)


@router.post("", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    request_data: ApprovalRequestCreate,
    current_user: User = Depends(require_permission("approval", "create")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new approval request
    """
    approval_service = ApprovalService(session)

    try:
        approval_request = await approval_service.create_request(
            requester=current_user,
            request_type=request_data.request_type,
            target_resource=request_data.target_resource,
            target_action=request_data.target_action,
            target_id=request_data.target_id,
            payload=request_data.payload,
            reason=request_data.reason,
        )

        return ApprovalRequestResponse.model_validate(approval_request)

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{request_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    request_id: int,
    decision: ApprovalDecision,
    current_user: User = Depends(require_permission("approval", "approve")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Approve an approval request (admin only)
    """
    approval_service = ApprovalService(session)

    try:
        approval_request = await approval_service.approve(
            request_id=request_id,
            approver=current_user,
            reason=decision.reason,
        )

        # Audit log
        await AuditService.log_approval(
            session=session,
            approver_id=current_user.id,
            request_id=request_id,
            action="approve",
            decision="approved",
        )

        return ApprovalRequestResponse.model_validate(approval_request)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, PermissionDeniedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{request_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    request_id: int,
    decision: ApprovalDecision,
    current_user: User = Depends(require_permission("approval", "approve")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Reject an approval request (admin only)
    """
    approval_service = ApprovalService(session)

    try:
        approval_request = await approval_service.reject(
            request_id=request_id,
            approver=current_user,
            reason=decision.reason,
        )

        # Audit log
        await AuditService.log_approval(
            session=session,
            approver_id=current_user.id,
            request_id=request_id,
            action="reject",
            decision="rejected",
        )

        return ApprovalRequestResponse.model_validate(approval_request)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, PermissionDeniedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{request_id}/cancel", response_model=ApprovalRequestResponse)
async def cancel_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Cancel an approval request (requester only)
    """
    approval_service = ApprovalService(session)

    try:
        approval_request = await approval_service.cancel(
            request_id=request_id,
            canceller=current_user,
        )

        # Audit log
        await AuditService.log(
            session=session,
            action="cancel_approval",
            resource_type="approval_request",
            status="success",
            user_id=current_user.id,
            resource_id=str(request_id),
        )

        return ApprovalRequestResponse.model_validate(approval_request)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, PermissionDeniedError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
