"""P0-3 统一 RBAC：验证 src.security.rbac 已被标记为 deprecated shim。"""
import warnings
import importlib
import importlib.util

import pytest


def test_security_rbac_import_raises_deprecation_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # 强制重新装载模块，捕获 import-time DeprecationWarning
        spec = importlib.util.find_spec("src.security.rbac")
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    dep_warns = [
        x for x in w
        if issubclass(x.category, DeprecationWarning)
        and "security.rbac" in str(x.message).lower()
    ]
    assert dep_warns, f"未抛出 DeprecationWarning: {w}"


def test_legacy_shim_still_has_compatible_api():
    """保持 test_rbac_abac 原有行为不变。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from src.security.rbac import RBACService
    service = RBACService()
    service.register_role("admin", {"knowledge.read", "knowledge.write", "task.execute", "workflow.approve", "audit.export"})
    service.assign_role("user-1", "admin")
    assert service.check_permission("user-1", "knowledge.write", resource="document") is True


def test_security_init_exports_preserved():
    """security.__init__ 中导出的名称未被移除。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from src.security import RBACService, Role, PermissionSet  # noqa: F401
    for sym in (RBACService, Role, PermissionSet):
        assert sym is not None


# ============================================================================
# OWNER+viewer 权限绕过回归：get_user_permissions 与 has_permission 一致性
# ============================================================================


@pytest.mark.asyncio
async def test_owner_viewer_permission_list_and_check_consistent():
    """OWNER demoted to viewer: list and check must agree, no full perms."""
    from unittest.mock import MagicMock
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, RBACService, has_permission

    user = MagicMock()
    user.id = 1
    user.is_active = True
    user.is_superuser = False
    user.account_type = AccountType.OWNER
    user.role = RoleEnum.VIEWER
    user.business_role = None
    user.permissions_config = None

    service = RBACService(session=MagicMock())
    perms = await service.get_user_permissions(user)

    all_codes = set(p.value for p in Permission)
    assert set(perms) <= all_codes
    for code in perms:
        perm = Permission(code)
        assert has_permission(user, perm) is True, (
            "get_user_permissions returned a permission that has_permission denies: %s" % code
        )
    denied = [p for p in Permission if p.value not in set(perms)]
    assert denied, "OWNER+viewer should not have all permissions"
    for perm in denied:
        assert has_permission(user, perm) is False


def test_accounts_is_owner_respects_viewer_demotion():
    """账号管理 _is_owner：OWNER 被降权为 viewer 后不得再管理子账号。"""
    from unittest.mock import MagicMock
    from src.api.routes.accounts import _is_owner
    from src.identity.models import AccountType, RoleEnum

    def _u(account_type, role, superuser=False):
        u = MagicMock()
        u.account_type = account_type
        u.role = role
        u.is_superuser = superuser
        return u

    # 正常主账号：允许
    assert _is_owner(_u(AccountType.OWNER, RoleEnum.USER)) is True
    assert _is_owner(_u(AccountType.OWNER, RoleEnum.ADMIN)) is True
    # 超级用户：允许
    assert _is_owner(_u(AccountType.SUB, RoleEnum.VIEWER, superuser=True)) is True
    # 子账号：拒绝
    assert _is_owner(_u(AccountType.SUB, RoleEnum.ADMIN)) is False
    # OWNER 被降权为 viewer：拒绝（与 has_permission 降权策略一致）
    assert _is_owner(_u(AccountType.OWNER, RoleEnum.VIEWER)) is False


# ============================================================================
# 权限码注册回归：所有路由 require_permission(resource, action) 必须能解析到
# 已注册的 Permission 枚举值，防止拼写错误导致 fail-closed 误锁（实测复现：
# business:metrics_read vs 枚举 business_metrics:read，OWNER 被 403）。
# ============================================================================


def test_all_route_permission_codes_are_registered():
    """静态审计：src/api/routes 下每个 require_permission 调用都必须命中真实枚举。"""
    import pathlib
    import re
    import src.api.routes as routes_pkg

    from src.identity.rbac import Permission

    valid_codes = {p.value for p in Permission}
    routes_dir = pathlib.Path(routes_pkg.__file__).parent
    pattern = re.compile(r'require_permission\(\s*"([^"]+)"\s*,\s*"([^"]+)"')

    violations = []
    total = 0
    for py_file in routes_dir.glob("*.py"):
        for match in pattern.finditer(py_file.read_text(encoding="utf-8")):
            total += 1
            code = f"{match.group(1)}:{match.group(2)}"
            if code not in valid_codes:
                violations.append(f"{py_file.name}: {code}")

    assert total > 50, "审计未找到足够的 require_permission 调用，模式可能失效"
    assert not violations, "以下权限码未在 Permission 枚举注册（会被 fail-closed 拒绝）:\n" + "\n".join(violations)


@pytest.mark.asyncio
async def test_owner_not_locked_out_by_unregistered_permission_code():
    """未注册权限码不得误锁 OWNER（老板）；子账号/降权账号仍 fail-closed。"""
    from unittest.mock import MagicMock
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import RBACService

    service = RBACService(session=MagicMock())

    owner = MagicMock()
    owner.id = 1
    owner.is_active = True
    owner.is_superuser = False
    owner.account_type = AccountType.OWNER
    owner.role = RoleEnum.USER
    owner.business_role = None
    owner.permissions_config = None

    # 即使权限码拼写错误/未注册，OWNER 也不应被 403 锁在门外
    assert await service.check_permission(owner, "business", "metrics_read") is True
    assert await service.check_permission(owner, "totally_unknown", "action") is True

    # 但被降权为 viewer 的 OWNER 仍然 fail-closed
    viewer_owner = MagicMock()
    viewer_owner.id = 2
    viewer_owner.is_active = True
    viewer_owner.is_superuser = False
    viewer_owner.account_type = AccountType.OWNER
    viewer_owner.role = RoleEnum.VIEWER
    viewer_owner.business_role = None
    viewer_owner.permissions_config = None
    assert await service.check_permission(viewer_owner, "totally_unknown", "action") is False

    # 普通子账号对未注册权限码 fail-closed
    sub = MagicMock()
    sub.id = 3
    sub.is_active = True
    sub.is_superuser = False
    sub.account_type = AccountType.SUB
    sub.role = RoleEnum.USER
    sub.business_role = None
    sub.permissions_config = None
    assert await service.check_permission(sub, "totally_unknown", "action") is False


@pytest.mark.asyncio
async def test_sub_account_with_granted_permission_passes_registered_code():
    """子账号持有已注册权限码时放行（业务角色/系统角色矩阵生效）。"""
    from unittest.mock import MagicMock
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import RBACService

    service = RBACService(session=MagicMock())

    sub = MagicMock()
    sub.id = 4
    sub.is_active = True
    sub.is_superuser = False
    sub.account_type = AccountType.SUB
    sub.role = RoleEnum.USER  # USER 矩阵含 business_metrics:read
    sub.business_role = None
    sub.permissions_config = None

    assert await service.check_permission(sub, "business_metrics", "read") is True
    assert await service.check_permission(sub, "quote", "create") is True
    assert await service.check_permission(sub, "platform", "update") is True
    # VIEWER 只读：quote:create 必须拒绝
    sub.role = RoleEnum.VIEWER
    assert await service.check_permission(sub, "quote", "create") is False
    assert await service.check_permission(sub, "quote", "read") is True
