"""
Tests for RBAC (Role-Based Access Control)
"""

from datetime import UTC, datetime

from src.identity.models import RoleEnum, User
from src.identity.rbac import Permission, has_permission, is_admin


def test_admin_has_all_permissions():
    """Test that admin role has all permissions"""
    admin_user = User(
        id=1,
        username="admin",
        email="admin@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert has_permission(admin_user, Permission.SYSTEM_ADMIN)
    assert has_permission(admin_user, Permission.USER_WRITE)
    assert has_permission(admin_user, Permission.POLICY_WRITE)


def test_user_limited_permissions():
    """Test that regular user has limited permissions"""
    regular_user = User(
        id=2,
        username="user",
        email="user@example.com",
        hashed_password="hashed",
        role=RoleEnum.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert has_permission(regular_user, Permission.SYSTEM_READ)
    assert has_permission(regular_user, Permission.USER_READ)
    assert not has_permission(regular_user, Permission.SYSTEM_ADMIN)
    assert not has_permission(regular_user, Permission.USER_WRITE)
    assert not has_permission(regular_user, Permission.POLICY_WRITE)


def test_viewer_minimal_permissions():
    """Test that viewer has minimal permissions"""
    viewer_user = User(
        id=3,
        username="viewer",
        email="viewer@example.com",
        hashed_password="hashed",
        role=RoleEnum.VIEWER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert has_permission(viewer_user, Permission.SYSTEM_READ)
    assert not has_permission(viewer_user, Permission.USER_READ)
    assert not has_permission(viewer_user, Permission.SYSTEM_WRITE)


def test_inactive_user_no_permissions():
    """Test that inactive user has no permissions (Fail Closed)"""
    inactive_user = User(
        id=4,
        username="inactive",
        email="inactive@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=False,  # Inactive
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Even admin permissions are denied when inactive
    assert not has_permission(inactive_user, Permission.SYSTEM_ADMIN)
    assert not has_permission(inactive_user, Permission.SYSTEM_READ)


def test_superuser_bypass():
    """Test that superuser bypasses role checks"""
    superuser = User(
        id=5,
        username="superuser",
        email="superuser@example.com",
        hashed_password="hashed",
        role=RoleEnum.VIEWER,  # Low role
        is_superuser=True,  # But is superuser
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Superuser has all permissions regardless of role
    assert has_permission(superuser, Permission.SYSTEM_ADMIN)
    assert has_permission(superuser, Permission.POLICY_WRITE)
    assert is_admin(superuser)
