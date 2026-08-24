"""
Test RBAC permission fix - admin user:read access
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.models import RoleEnum, User
from src.identity.rbac import ROLE_PERMISSIONS, Permission, RBACService


def test_user_read_permission_exists():
    """Test that user:read permission exists in Permission enum"""
    assert Permission.USER_READ.value == "user:read"


def test_admin_has_user_read_permission():
    """Test that ADMIN role has user:read permission"""
    admin_perms = ROLE_PERMISSIONS[RoleEnum.ADMIN]
    assert Permission.USER_READ in admin_perms


def test_regular_user_has_user_read_permission():
    """Test that USER role also has user:read permission"""
    user_perms = ROLE_PERMISSIONS[RoleEnum.USER]
    assert Permission.USER_READ in user_perms


@pytest.mark.asyncio
async def test_admin_can_check_user_read_permission(
    admin_user: User,
    async_session: AsyncSession,
):
    """Test that admin user can check user:read permission"""
    rbac = RBACService(async_session)

    has_perm = await rbac.check_permission(
        user=admin_user,
        resource="user",
        action="read",
    )

    assert has_perm is True


@pytest.mark.asyncio
async def test_regular_user_can_check_user_read_permission(
    regular_user: User,
    async_session: AsyncSession,
):
    """Test that regular user can also check user:read permission"""
    rbac = RBACService(async_session)

    has_perm = await rbac.check_permission(
        user=regular_user,
        resource="user",
        action="read",
    )

    assert has_perm is True


@pytest.mark.asyncio
async def test_old_plural_users_read_fails(
    admin_user: User,
    async_session: AsyncSession,
):
    """Test that old plural 'users:read' permission fails (doesn't exist)"""
    rbac = RBACService(async_session)

    # This should fail because "users:read" (plural) is not in Permission enum
    has_perm = await rbac.check_permission(
        user=admin_user,
        resource="users",  # Wrong - should be "user"
        action="read",
    )

    # Should be False because the permission string doesn't match
    assert has_perm is False


@pytest.mark.asyncio
async def test_get_admin_user_permissions(
    admin_user: User,
    async_session: AsyncSession,
):
    """Test listing all admin permissions"""
    rbac = RBACService(async_session)

    perms = await rbac.get_user_permissions(admin_user)

    assert "user:read" in perms
    assert "user:write" in perms
    assert "user:delete" in perms
