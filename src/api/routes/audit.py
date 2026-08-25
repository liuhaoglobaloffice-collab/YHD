"""
Audit log API routes
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import AuditLogListResponse, AuditLogResponse
from src.identity.audit import AuditService
from src.identity.database import get_db_session
from src.identity.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Query audit logs with filters

    - Admin: can query all logs
    - User: can only query their own logs
    """
    # Non-admin users can only see their own logs
    if current_user.role.value != "admin":
        if user_id is not None and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own audit logs",
            )
        user_id = current_user.id

    # Query logs
    logs = await AuditService.query_logs(
        session=session,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),  # Note: This is not the total count, just returned count
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get specific audit log by ID
    """
    result = await session.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log {log_id} not found",
        )

    # Non-admin users can only see their own logs
    if current_user.role.value != "admin" and log.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own audit logs",
        )

    return AuditLogResponse.model_validate(log)
