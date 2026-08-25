"""
Permission management API routes
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.identity.database import get_db_session
from src.identity.models import User
from src.identity.rbac import PERMISSIONS, ROLE_PERMISSIONS

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=List[dict])
async def list_permissions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all available permissions

    For Stage 2, returns the static permission list from RBAC module.
    Future: migrate to flexible Permission model in database.
    """
    # Return static permissions from RBACService
    permissions = [
        {
            "code": perm.value,
            "resource": perm.value.split(":")[0] if ":" in perm.value else perm.value,
            "action": perm.value.split(":")[1] if ":" in perm.value else "execute",
            "description": f"Permission: {perm.value}",
        }
        for perm in PERMISSIONS
    ]

    return permissions


@router.get("/by-role/{role_name}", response_model=List[dict])
async def get_role_permissions(
    role_name: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get permissions for a specific role
    """
    role_upper = role_name.upper()

    if role_upper not in ROLE_PERMISSIONS:
        return []

    role_perms = ROLE_PERMISSIONS[role_upper]

    permissions = [
        {
            "code": perm.value,
            "resource": perm.value.split(":")[0] if ":" in perm.value else perm.value,
            "action": perm.value.split(":")[1] if ":" in perm.value else "execute",
            "description": f"Permission: {perm.value}",
        }
        for perm in role_perms
    ]

    return permissions
