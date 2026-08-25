"""
User management API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_permission
from src.api.schemas import (
    UserListResponse,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from src.core.errors import PermissionDeniedError, ResourceNotFoundError
from src.identity.audit import AuditService
from src.identity.database import get_db_session
from src.identity.governance import IdentityGovernanceService
from src.identity.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission("user", "read")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all users (admin only)
    """
    # Count total
    count_result = await session.execute(select(func.count(User.id)))
    total = count_result.scalar_one()

    # Get users
    result = await session.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = list(result.scalars().all())

    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("user", "read")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get user by ID
    """
    gov_service = IdentityGovernanceService(session)
    try:
        user = await gov_service.get_user(user_id)
        return UserResponse.model_validate(user)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    update: UserStatusUpdate,
    current_user: User = Depends(require_permission("user", "disable")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Enable or disable user (admin only)
    """
    gov_service = IdentityGovernanceService(session)

    try:
        if update.is_active:
            user = await gov_service.enable_user(user_id, current_user)
            action = "enable_user"
        else:
            user = await gov_service.disable_user(user_id, current_user)
            action = "disable_user"

        # Audit log
        await AuditService.log_success(
            session=session,
            action=action,
            resource_type="user",
            user_id=current_user.id,
            resource_id=str(user_id),
            details={"is_active": update.is_active},
        )

        return UserResponse.model_validate(user)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    update: UserRoleUpdate,
    current_user: User = Depends(require_permission("user", "update_role")),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Change user role (admin only)
    """
    gov_service = IdentityGovernanceService(session)

    try:
        # Get current user to log old role
        target_user = await gov_service.get_user(user_id)
        old_role = target_user.role

        # Change role
        user = await gov_service.change_user_role(
            user_id=user_id,
            new_role=update.role,
            actor=current_user,
        )

        # Audit log
        await AuditService.log_role_change(
            session=session,
            actor_id=current_user.id,
            target_user_id=user_id,
            old_role=old_role.value,
            new_role=update.role.value,
        )

        return UserResponse.model_validate(user)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
