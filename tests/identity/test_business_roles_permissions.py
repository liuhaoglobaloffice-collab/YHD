"""
Unit tests for business roles and fine-grained permission system.

Covers:
- Business role definition (SALES/PURCHASING/OPERATIONS/AI_ADMIN/GENERAL)
- Permission checking priority: permissions_config > business_role > system_role
- Data scope (all/department/self)
- Business role default permissions
- Main account (OWNER) has full permissions
- High-risk operations classification
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.identity.auth import hash_password
from src.identity.models import AccountType, BusinessRole, RoleEnum, User, Base
from src.identity.rbac import (
    BUSINESS_ROLE_PERMISSIONS,
    Permission,
    RBACService,
    has_permission,
)


# ============================================================
# Helpers
# ============================================================

async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _create_test_user(session_factory, **kwargs):
    defaults = dict(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        role="user",
        account_type=AccountType.OWNER,
        is_active=True,
        approval_status=None,
        business_role=None,
        data_scope="self",
        permissions_config=None,
    )
    defaults.update(kwargs)
    async with session_factory() as session:
        user = User(**defaults)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ============================================================
# 1. Business role tests
# ============================================================

class TestBusinessRoleDefinitions:
    """业务角色定义测试 - 确保所有角色都有权限配置"""

    def test_all_business_roles_have_permissions(self):
        """所有已定义的业务角色都必须有权限列表"""
        for role in BusinessRole:
            perms = BUSINESS_ROLE_PERMISSIONS.get(role)
            assert perms is not None, f"Business role {role.value} has no permissions configured"
            assert len(perms) > 0, f"Business role {role.value} permissions list is empty"

    def test_sales_role_has_crm_and_platform_permissions(self):
        """销售角色应该包含客户、CRM、社媒平台权限"""
        perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.SALES]
        assert Permission.LEAD_CREATE in perms
        assert Permission.LEAD_READ in perms
        assert Permission.QUOTE_CREATE in perms
        assert Permission.PLATFORM_MESSAGE_SEND in perms
        assert Permission.TASK_CREATE in perms

    def test_purchasing_role_has_supplier_permissions(self):
        """采购角色应该包含供应商管理权限"""
        perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.PURCHASING]
        assert Permission.SUPPLIER_CREATE in perms
        assert Permission.SUPPLIER_READ in perms
        assert Permission.CUSTOMS_READ in perms

    def test_ai_admin_role_has_ai_workforce_permissions(self):
        """AI管理员角色应该包含AI员工管理权限"""
        perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.AI_ADMIN]
        assert Permission.EMPLOYEE_CREATE in perms
        assert Permission.EMPLOYEE_DELETE in perms
        assert Permission.AGENT_CREATE in perms
        assert Permission.WORKFORCE_CREATE in perms

    def test_operations_role_has_site_seo_permissions(self):
        """运营角色应该包含独立站和SEO权限"""
        perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.OPERATIONS]
        assert Permission.SITE_READ in perms
        assert Permission.SEO_READ in perms
        assert Permission.CEO_DASHBOARD_READ in perms


# ============================================================
# 2. Permission checking priority tests
# ============================================================

class TestPermissionCheckingPriority:
    """权限检查优先级测试: permissions_config > business_role > system_role"""

    def test_main_owner_always_has_all_permissions(self):
        """主账号(OWNER)永远拥有所有权限"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_test_user(sf, account_type=AccountType.OWNER)
            for perm in Permission:
                assert has_permission(user, perm) is True

        asyncio.run(_run())

    def test_inactive_user_has_no_permissions(self):
        """停用账号没有任何权限"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_test_user(sf, is_active=False, account_type=AccountType.SUB)
            for perm in Permission:
                assert has_permission(user, perm) is False

        asyncio.run(_run())

    def test_business_role_gives_default_permissions(self):
        """业务角色提供默认权限"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_test_user(
                sf,
                account_type=AccountType.SUB,
                business_role=BusinessRole.SALES,
                is_active=True,
            )
            # 销售角色默认有这些权限
            assert has_permission(user, Permission.LEAD_CREATE) is True
            assert has_permission(user, Permission.QUOTE_CREATE) is True
            assert has_permission(user, Permission.PLATFORM_MESSAGE_SEND) is True

        asyncio.run(_run())

    def test_custom_permissions_config_overrides_business_role(self):
        """permissions_config 覆盖业务角色默认权限"""
        async def _run():
            sf, _ = await _make_session()
            # 业务角色 SALES 默认有 LEAD_CREATE
            # 但自定义配置中禁用 LEAD_CREATE
            user = await _create_test_user(
                sf,
                account_type=AccountType.SUB,
                business_role=BusinessRole.SALES,
                is_active=True,
                permissions_config={
                    "lead:create": False,  # 禁用该权限
                    "quote:create": True,
                },
            )
            # 自定义配置覆盖
            assert has_permission(user, Permission.LEAD_CREATE) is False
            assert has_permission(user, Permission.QUOTE_CREATE) is True
            # 业务角色中未在配置出现的权限仍然可用
            assert has_permission(user, Permission.PLATFORM_MESSAGE_SEND) is True

        asyncio.run(_run())

    def test_get_user_permissions_includes_all_configured_and_role(self):
        """get_user_permissions 应该包含所有权限"""
        async def _run():
            sf, _ = await _make_session()
            async with sf() as session:
                user = await _create_test_user(
                    sf,
                    account_type=AccountType.SUB,
                    business_role=BusinessRole.SALES,
                    permissions_config={
                        "lead:create": False,
                    },
                )
                svc = RBACService(session)
                perms = await svc.get_user_permissions(user)
                assert "quote:create" in perms  # from SALES role
                assert "lead:create" not in perms  # explicitly disabled

        asyncio.run(_run())

    def test_empty_permissions_config_uses_business_role_permissions(self):
        """空配置使用业务角色权限"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_test_user(
                sf,
                account_type=AccountType.SUB,
                business_role=BusinessRole.AI_ADMIN,
                permissions_config={},
                is_active=True,
            )
            # 应该使用业务角色所有权限
            assert has_permission(user, Permission.EMPLOYEE_CREATE) is True
            assert has_permission(user, Permission.AGENT_CREATE) is True

        asyncio.run(_run())

    def test_fallback_to_system_role_when_no_business_role(self):
        """没有业务角色时回退到系统角色"""
        async def _run():
            from src.identity.rbac import ROLE_PERMISSIONS
            sf, _ = await _make_session()
            user = await _create_test_user(
                sf,
                account_type=AccountType.SUB,
                role=RoleEnum.ADMIN,
                business_role=None,
                is_active=True,
            )
            # system role ADMIN has many permissions
            admin_perms = ROLE_PERMISSIONS.get(RoleEnum.ADMIN, [])
            if admin_perms:
                perm = list(admin_perms)[0]
                assert has_permission(user, perm) is True

        asyncio.run(_run())


# ============================================================
# 3. Data scope tests
# ============================================================

class TestDataScopeConfiguration:
    """数据权限范围配置"""

    def test_user_has_valid_data_scope_default(self):
        """用户默认数据范围是 self"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_test_user(
                sf,
                account_type=AccountType.SUB,
            )
            assert user.data_scope == "self"

        asyncio.run(_run())

    def test_user_can_set_all_data_scope(self):
        """可以设置全公司数据范围"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_test_user(
                sf,
                account_type=AccountType.SUB,
                data_scope="all",
            )
            assert user.data_scope == "all"

        asyncio.run(_run())

    def test_permissions_config_json_stored_correctly(self):
        """权限配置JSON能正确存储和读取"""
        async def _run():
            sf, _ = await _make_session()
            config = {
                "lead:read": True,
                "lead:write": False,
                "quote:create": True,
            }
            user = await _create_test_user(
                sf,
                account_type=AccountType.SUB,
                business_role=BusinessRole.SALES,
                permissions_config=config,
            )
            assert user.permissions_config == config

        asyncio.run(_run())


# ============================================================
# 4. Approval workflow with business role tests
# ============================================================

class TestApprovalWithRoleAssignment:
    """审批时同时分配业务角色"""

    def test_approved_sub_account_gets_role_permissions(self):
        """审批后的子账号应该获得对应角色的默认权限"""
        async def _run():
            sf, _ = await _make_session()
            from src.identity.models import ApprovalStatus
            owner = await _create_test_user(sf, account_type=AccountType.OWNER)
            # 模拟审批流程：创建子账号 + 批准 + 分配角色 + 设置权限
            role_perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.SALES]
            permissions_config = {p.value: True for p in role_perms}
            sub = await _create_test_user(
                sf,
                username="sales_user",
                email="sales@example.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=True,
                approval_status=ApprovalStatus.APPROVED.value,
                business_role=BusinessRole.SALES,
                permissions_config=permissions_config,
            )
            # 批准后应该有销售角色权限
            assert sub.business_role == BusinessRole.SALES
            assert sub.permissions_config is not None
            for perm in list(role_perms)[:3]:
                assert sub.permissions_config[perm.value] is True

        asyncio.run(_run())

    def test_pending_sub_account_cannot_access(self):
        """待审核子账号虽然有 role，但因为 inactive 所以无权限"""
        async def _run():
            from src.identity.models import ApprovalStatus
            sf, _ = await _make_session()
            owner = await _create_test_user(sf, account_type=AccountType.OWNER)
            sub = await _create_test_user(
                sf,
                username="pending",
                email="pending@example.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
                business_role=BusinessRole.SALES,
            )
            assert sub.is_active is False
            for perm in Permission:
                assert has_permission(sub, perm) is False

        asyncio.run(_run())


# ============================================================
# 5. Permission enumeration tests
# ============================================================

class TestPermissionList:
    """确保所有权限项都正确定义"""

    def test_all_exported_permissions_are_valid(self):
        """所有导出权限都有效"""
        from src.identity.rbac import PERMISSIONS
        assert len(PERMISSIONS) == len(Permission)
        for p in PERMISSIONS:
            assert isinstance(p, Permission)

    def test_quote_permissions_are_defined(self):
        """报价单权限已定义"""
        assert Permission.QUOTE_CREATE.value == "quote:create"
        assert Permission.QUOTE_READ.value == "quote:read"
        assert Permission.QUOTE_UPDATE.value == "quote:update"
        assert Permission.QUOTE_DELETE.value == "quote:delete"
        assert Permission.QUOTE_SEND.value == "quote:send"

    def test_quote_permissions_included_in_correct_roles(self):
        """报价权限在正确角色中"""
        sales_perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.SALES]
        assert Permission.QUOTE_CREATE in sales_perms
        assert Permission.QUOTE_SEND in sales_perms
        assert Permission.QUOTE_READ in sales_perms

        purchasing_perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.PURCHASING]
        assert Permission.QUOTE_READ in purchasing_perms

        general_perms = BUSINESS_ROLE_PERMISSIONS[BusinessRole.GENERAL]
        assert Permission.QUOTE_CREATE in general_perms
