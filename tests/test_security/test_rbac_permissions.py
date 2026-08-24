"""
Phase 2F-3.2 Security Testing
Test RBAC permission enforcement across API layer

Architecture Test:
    API → Permission Check → RBAC Service → Database

Security Principles:
    - Security First
    - Fail Closed (default DENY)
    - Audit Everything
"""

from unittest.mock import AsyncMock

import pytest

from src.core.errors import PermissionDeniedError
from src.identity.models import User
from src.identity.rbac import Permission, RBACService, RoleEnum


class TestPermissionEnum:
    """Test Permission enum completeness"""

    def test_stage2_permissions_exist(self):
        """Test Stage 2 (Identity + Governance) permissions"""
        assert Permission.USER_READ
        assert Permission.USER_WRITE
        assert Permission.ROLE_READ
        assert Permission.AUDIT_READ
        assert Permission.APPROVAL_CREATE
        assert Permission.POLICY_READ

    def test_stage4_permissions_exist(self):
        """Test Stage 4 (Knowledge) permissions"""
        assert Permission.KNOWLEDGE_READ
        assert Permission.KNOWLEDGE_WRITE
        assert Permission.KNOWLEDGE_DELETE

    def test_stage5_task_permissions_exist(self):
        """Test Stage 5 Task permissions"""
        assert Permission.TASK_CREATE
        assert Permission.TASK_READ
        assert Permission.TASK_UPDATE
        assert Permission.TASK_DELETE
        assert Permission.TASK_EXECUTE
        assert Permission.TASK_ASSIGN

    def test_stage5_workflow_permissions_exist(self):
        """Test Stage 5 Workflow permissions"""
        assert Permission.WORKFLOW_CREATE
        assert Permission.WORKFLOW_READ
        assert Permission.WORKFLOW_UPDATE
        assert Permission.WORKFLOW_DELETE
        assert Permission.WORKFLOW_EXECUTE

    def test_stage6_agent_permissions_exist(self):
        """Test Stage 6 AI Agent permissions (Phase 2F-3.2)"""
        assert Permission.AGENT_CREATE
        assert Permission.AGENT_READ
        assert Permission.AGENT_UPDATE
        assert Permission.AGENT_DELETE
        assert Permission.AGENT_EXECUTE

    def test_stage6_workforce_permissions_exist(self):
        """Test Stage 6 AI Workforce permissions (Phase 2F-3.2)"""
        assert Permission.WORKFORCE_CREATE
        assert Permission.WORKFORCE_READ
        assert Permission.WORKFORCE_UPDATE
        assert Permission.WORKFORCE_DELETE
        assert Permission.EMPLOYEE_CREATE
        assert Permission.EMPLOYEE_READ
        assert Permission.EMPLOYEE_UPDATE
        assert Permission.EMPLOYEE_DELETE
        assert Permission.EMPLOYEE_ACTIVATE
        assert Permission.EMPLOYEE_SUSPEND
        assert Permission.EMPLOYEE_RETIRE
        assert Permission.EMPLOYEE_PERFORMANCE_READ
        assert Permission.EMPLOYEE_COST_READ

    def test_stage7_business_permissions_exist(self):
        """Test Stage 7 Business OS permissions (Phase 2F-3.2)"""
        assert Permission.BUSINESS_CREATE
        assert Permission.BUSINESS_READ
        assert Permission.BUSINESS_UPDATE
        assert Permission.BUSINESS_DELETE
        assert Permission.BUSINESS_EXECUTE
        assert Permission.BUSINESS_TASK_CREATE
        assert Permission.BUSINESS_TASK_READ
        assert Permission.BUSINESS_TASK_UPDATE
        assert Permission.BUSINESS_TASK_DELETE
        assert Permission.BUSINESS_METRICS_READ

    def test_stage8_ceo_permissions_exist(self):
        """Test Stage 8 CEO AI OS permissions (Phase 2F-3.2)"""
        assert Permission.CEO_COMMAND_EXECUTE
        assert Permission.CEO_ANALYTICS_READ
        assert Permission.CEO_SYSTEM_CONTROL
        assert Permission.CEO_WORKFORCE_MANAGE
        assert Permission.CEO_DASHBOARD_READ


class TestRolePermissionMapping:
    """Test role-permission mappings"""

    def test_admin_has_all_permissions(self):
        """Test ADMIN role has full system access"""
        from src.identity.rbac import ROLE_PERMISSIONS

        admin_perms = ROLE_PERMISSIONS[RoleEnum.ADMIN]

        # Stage 1-5 permissions
        assert Permission.USER_WRITE in admin_perms
        assert Permission.TASK_DELETE in admin_perms
        assert Permission.WORKFLOW_EXECUTE in admin_perms

        # Stage 6 permissions (Phase 2F-3.2)
        assert Permission.AGENT_CREATE in admin_perms
        assert Permission.WORKFORCE_DELETE in admin_perms
        assert Permission.EMPLOYEE_RETIRE in admin_perms

        # Stage 7 permissions (Phase 2F-3.2)
        assert Permission.BUSINESS_DELETE in admin_perms
        assert Permission.BUSINESS_METRICS_READ in admin_perms

        # Stage 8 permissions (Phase 2F-3.2)
        assert Permission.CEO_COMMAND_EXECUTE in admin_perms
        assert Permission.CEO_SYSTEM_CONTROL in admin_perms

    def test_user_has_operational_permissions(self):
        """Test USER role has operational but not destructive permissions"""
        from src.identity.rbac import ROLE_PERMISSIONS

        user_perms = ROLE_PERMISSIONS[RoleEnum.USER]

        # Should have operational permissions
        assert Permission.TASK_CREATE in user_perms
        assert Permission.WORKFLOW_EXECUTE in user_perms
        assert Permission.BUSINESS_CREATE in user_perms

        # Should NOT have destructive permissions
        assert Permission.USER_DELETE not in user_perms
        assert Permission.WORKFORCE_DELETE not in user_perms
        assert Permission.CEO_SYSTEM_CONTROL not in user_perms

    def test_viewer_has_readonly_permissions(self):
        """Test VIEWER role has read-only permissions"""
        from src.identity.rbac import ROLE_PERMISSIONS

        viewer_perms = ROLE_PERMISSIONS[RoleEnum.VIEWER]

        # Should have read permissions
        assert Permission.TASK_READ in viewer_perms
        assert Permission.WORKFLOW_READ in viewer_perms
        assert Permission.BUSINESS_READ in viewer_perms
        assert Permission.EMPLOYEE_READ in viewer_perms

        # Should NOT have write permissions
        assert Permission.TASK_CREATE not in viewer_perms
        assert Permission.WORKFLOW_EXECUTE not in viewer_perms
        assert Permission.BUSINESS_CREATE not in viewer_perms
        assert Permission.EMPLOYEE_CREATE not in viewer_perms


class TestRBACServicePermissionChecks:
    """Test RBACService permission checking"""

    @pytest.mark.asyncio
    async def test_admin_permission_check(self):
        """Test admin user permission check"""
        admin_user = User(
            id=1,
            username="admin",
            email="admin@test.com",
            role=RoleEnum.ADMIN,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Admin should have business create permission
        has_perm = await rbac.check_permission(
            user=admin_user,
            resource="business",
            action="create",
        )

        assert has_perm is True

    @pytest.mark.asyncio
    async def test_user_permission_check(self):
        """Test regular user permission check"""
        user = User(
            id=2,
            username="user",
            email="user@test.com",
            role=RoleEnum.USER,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # User should have business read permission
        has_perm = await rbac.check_permission(
            user=user,
            resource="business",
            action="read",
        )

        assert has_perm is True

    @pytest.mark.asyncio
    async def test_user_denied_destructive_permission(self):
        """Test user denied destructive permission (Fail Closed)"""
        user = User(
            id=2,
            username="user",
            email="user@test.com",
            role=RoleEnum.USER,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # User should NOT have business delete permission
        has_perm = await rbac.check_permission(
            user=user,
            resource="business",
            action="delete",
        )

        assert has_perm is False

    @pytest.mark.asyncio
    async def test_viewer_permission_check(self):
        """Test viewer user permission check"""
        viewer = User(
            id=3,
            username="viewer",
            email="viewer@test.com",
            role=RoleEnum.VIEWER,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Viewer should have read permission
        has_perm = await rbac.check_permission(
            user=viewer,
            resource="workflow",
            action="read",
        )

        assert has_perm is True

    @pytest.mark.asyncio
    async def test_viewer_denied_write_permission(self):
        """Test viewer denied write permission (Fail Closed)"""
        viewer = User(
            id=3,
            username="viewer",
            email="viewer@test.com",
            role=RoleEnum.VIEWER,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Viewer should NOT have create permission
        has_perm = await rbac.check_permission(
            user=viewer,
            resource="workflow",
            action="create",
        )

        assert has_perm is False

    @pytest.mark.asyncio
    async def test_inactive_user_denied(self):
        """Test inactive user denied all permissions (Fail Closed)"""
        inactive_user = User(
            id=4,
            username="inactive",
            email="inactive@test.com",
            role=RoleEnum.USER,
            is_active=False,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Inactive user should be denied
        has_perm = await rbac.check_permission(
            user=inactive_user,
            resource="task",
            action="read",
        )

        assert has_perm is False

    @pytest.mark.asyncio
    async def test_superuser_bypass(self):
        """Test superuser bypasses all permission checks"""
        superuser = User(
            id=0,
            username="superuser",
            email="super@test.com",
            role=RoleEnum.ADMIN,
            is_active=True,
            is_superuser=True,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Superuser should have any permission
        has_perm = await rbac.check_permission(
            user=superuser,
            resource="ceo",
            action="system_control",
        )

        assert has_perm is True

    @pytest.mark.asyncio
    async def test_require_permission_async_success(self):
        """Test require_permission_async allows authorized user"""
        admin_user = User(
            id=1,
            username="admin",
            email="admin@test.com",
            role=RoleEnum.ADMIN,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Should not raise exception
        await rbac.require_permission_async(
            user=admin_user,
            resource="employee",
            action="create",
        )

    @pytest.mark.asyncio
    async def test_require_permission_async_denied(self):
        """Test require_permission_async denies unauthorized user (Fail Closed)"""
        viewer = User(
            id=3,
            username="viewer",
            email="viewer@test.com",
            role=RoleEnum.VIEWER,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Should raise PermissionDeniedError
        with pytest.raises(PermissionDeniedError):
            await rbac.require_permission_async(
                user=viewer,
                resource="employee",
                action="create",
            )

    @pytest.mark.asyncio
    async def test_require_permission_async_no_user(self):
        """Test require_permission_async denies None user (Fail Closed)"""
        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Should raise PermissionDeniedError
        with pytest.raises(PermissionDeniedError):
            await rbac.require_permission_async(
                user=None,
                resource="task",
                action="create",
            )


class TestFailClosedPrinciple:
    """Test Fail Closed security principle"""

    @pytest.mark.asyncio
    async def test_unknown_permission_denied(self):
        """Test unknown permission defaults to DENY (Fail Closed)"""
        user = User(
            id=2,
            username="user",
            email="user@test.com",
            role=RoleEnum.USER,
            is_active=True,
            is_superuser=False,
        )

        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # Unknown resource:action should be denied
        has_perm = await rbac.check_permission(
            user=user,
            resource="unknown_resource",
            action="unknown_action",
        )

        assert has_perm is False

    @pytest.mark.asyncio
    async def test_no_user_denied(self):
        """Test None user denied all permissions (Fail Closed)"""
        session_mock = AsyncMock()
        rbac = RBACService(session_mock)

        # None user should raise PermissionDeniedError
        with pytest.raises(PermissionDeniedError):
            await rbac.require_permission_async(
                user=None,
                resource="task",
                action="read",
            )

    def test_disabled_user_denied(self):
        """Test disabled user denied all permissions (Fail Closed)"""
        from src.identity.rbac import has_permission

        disabled_user = User(
            id=5,
            username="disabled",
            email="disabled@test.com",
            role=RoleEnum.USER,
            is_active=False,
            is_superuser=False,
        )

        # Disabled user should be denied
        has_perm = has_permission(disabled_user, Permission.TASK_READ)

        assert has_perm is False


class TestPermissionDependency:
    """Test FastAPI permission dependency"""

    @pytest.mark.asyncio
    async def test_require_permission_dependency_exists(self):
        """Test require_permission dependency function exists"""
        from src.api.dependencies.permissions import require_permission

        assert callable(require_permission)

    @pytest.mark.asyncio
    async def test_require_any_permission_dependency_exists(self):
        """Test require_any_permission dependency function exists"""
        from src.api.dependencies.permissions import require_any_permission

        assert callable(require_any_permission)

    @pytest.mark.asyncio
    async def test_require_admin_dependency_exists(self):
        """Test require_admin dependency function exists"""
        from src.api.dependencies.permissions import require_admin

        assert callable(require_admin)

    def test_permission_dependency_returns_callable(self):
        """Test require_permission returns a callable dependency"""
        from src.api.dependencies.permissions import require_permission

        # Should return a dependency function
        dep = require_permission("task", "create")
        assert callable(dep)

    def test_any_permission_dependency_returns_callable(self):
        """Test require_any_permission returns a callable dependency"""
        from src.api.dependencies.permissions import require_any_permission

        # Should return a dependency function
        dep = require_any_permission([("task", "create"), ("workflow", "create")])
        assert callable(dep)

    def test_admin_dependency_returns_callable(self):
        """Test require_admin returns a callable dependency"""
        from src.api.dependencies.permissions import require_admin

        # Should return a dependency function
        dep = require_admin()
        assert callable(dep)


# Test Coverage Summary
def test_phase2f3_2_test_count():
    """Verify Phase 2F-3.2 test count meets requirement"""
    import inspect

    # Count test methods
    test_count = 0
    for name, obj in inspect.getmembers(TestPermissionEnum):
        if name.startswith("test_"):
            test_count += 1

    for name, obj in inspect.getmembers(TestRolePermissionMapping):
        if name.startswith("test_"):
            test_count += 1

    for name, obj in inspect.getmembers(TestRBACServicePermissionChecks):
        if name.startswith("test_"):
            test_count += 1

    for name, obj in inspect.getmembers(TestFailClosedPrinciple):
        if name.startswith("test_"):
            test_count += 1

    for name, obj in inspect.getmembers(TestPermissionDependency):
        if name.startswith("test_"):
            test_count += 1

    # Phase 2F-3.2 requires minimum 30 security tests
    assert test_count >= 30, f"Expected >=30 tests, got {test_count}"
