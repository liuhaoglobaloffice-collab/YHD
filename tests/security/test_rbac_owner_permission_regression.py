"""Y1.0 安全回归：OWNER 降权为 viewer 的权限绕过修复，不得矫枉过正。

背景（已修复的 P0 安全缺口）：
    src/identity/rbac.py::has_permission() 曾写作
        if user.account_type == AccountType.OWNER: return True
    主账号（老板）只要 account_type=OWNER 就无视 role，被降权成 viewer 后
    依然能写数据（实测复现于 tests/api/test_memory_crud.py）。

修复后：
        if user.account_type == AccountType.OWNER and user.role != RoleEnum.VIEWER:
            return True

本文件的职责（与既有 test_rbac_unified.py 互补，不重复）：
    既有测试只锁定了「OWNER+viewer 被拒绝」这一侧。
    本文件锁定**另一侧**：修复不能把老板的正常权限也砍掉——
      - OWNER + admin  → 完整权限（含 SYSTEM_ADMIN / USER_DELETE 等高危写权限）
      - OWNER + user   → 完整权限
      - OWNER + viewer → 只保留 viewer 角色矩阵内的只读权限
      - SUB   + user   → 严格按 RoleEnum.USER 权限矩阵，不享受 OWNER 特权
      - SUB   + viewer → 只读
    并做 HTTP 端到端验证（真实 TestClient + 真实 SQLite），确保单元层
    的 has_permission() 与线上路由实际放行行为一致。
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest


# ============================================================================
# 单元测试：has_permission() 权限矩阵
# ============================================================================


def _mk_user(account_type, role, *, superuser=False, business_role=None,
             permissions_config=None, active=True):
    """构造一个满足 has_permission() 鸭子类型契约的用户对象。"""
    u = MagicMock()
    u.id = 1
    u.is_active = active
    u.is_superuser = superuser
    u.account_type = account_type
    u.role = role
    u.business_role = business_role
    u.permissions_config = permissions_config
    return u


# 只有 OWNER 特权路径才可能放行的高危权限（viewer 角色矩阵中绝不包含）
PRIVILEGED_WRITE = [
    "system:admin",
    "user:delete",
    "user:grant_admin",
    "knowledge:write",
    "knowledge:delete",
    "task:delete",
    "workflow:delete",
    "audit:export",
]

# viewer 角色矩阵内应有的只读权限
VIEWER_READ = [
    "system:read",
    "knowledge:read",
    "task:read",
    "workflow:read",
    "audit:read",
    "lead:read",
]


def test_owner_admin_keeps_full_permissions():
    """修复不得矫枉过正：OWNER + admin 必须仍是全权。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, has_permission

    user = _mk_user(AccountType.OWNER, RoleEnum.ADMIN)

    for code in PRIVILEGED_WRITE:
        assert has_permission(user, Permission(code)) is True, (
            f"OWNER+admin 被误伤，失去高危权限 {code}"
        )
    for code in VIEWER_READ:
        assert has_permission(user, Permission(code)) is True, code

    # 全枚举逐个校验：OWNER+admin 必须拥有全部权限
    for perm in Permission:
        assert has_permission(user, perm) is True, f"OWNER+admin 缺少 {perm.value}"


def test_owner_user_keeps_full_permissions():
    """修复不得矫枉过正：OWNER + user（默认角色）必须仍是全权。

    老板注册时默认 role=user，若此处被砍，等于全站老板账号集体降级。
    """
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, has_permission

    user = _mk_user(AccountType.OWNER, RoleEnum.USER)

    for code in PRIVILEGED_WRITE:
        assert has_permission(user, Permission(code)) is True, (
            f"OWNER+user 被误伤，失去高危权限 {code}"
        )
    for perm in Permission:
        assert has_permission(user, perm) is True, f"OWNER+user 缺少 {perm.value}"


def test_owner_viewer_loses_write_but_keeps_read():
    """OWNER 被显式降权为 viewer：写权限全部拒绝，读权限保留。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, has_permission

    user = _mk_user(AccountType.OWNER, RoleEnum.VIEWER)

    for code in PRIVILEGED_WRITE:
        assert has_permission(user, Permission(code)) is False, (
            f"OWNER+viewer 仍能写 {code}，权限绕过未修复"
        )
    for code in VIEWER_READ:
        assert has_permission(user, Permission(code)) is True, (
            f"OWNER+viewer 应保留只读权限 {code}"
        )


def test_sub_user_follows_role_matrix_not_owner_privilege():
    """SUB + user：严格走 RoleEnum.USER 权限矩阵，不享受 OWNER 全权。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, has_permission

    user = _mk_user(AccountType.SUB, RoleEnum.USER)

    # USER 矩阵内的权限 → 放行
    for code in ("knowledge:write", "task:create", "task:execute", "lead:create",
                 "supplier:create", "site:update", "quote:send"):
        assert has_permission(user, Permission(code)) is True, f"SUB+user 应拥有 {code}"

    # USER 矩阵外的高危权限 → 拒绝
    for code in ("system:admin", "user:delete", "user:grant_admin",
                 "knowledge:delete", "task:delete", "workflow:delete",
                 "audit:export", "employee:delete"):
        assert has_permission(user, Permission(code)) is False, (
            f"SUB+user 不应拥有 {code}"
        )


def test_sub_viewer_is_read_only():
    """SUB + viewer：只读。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, has_permission

    user = _mk_user(AccountType.SUB, RoleEnum.VIEWER)

    for code in PRIVILEGED_WRITE:
        assert has_permission(user, Permission(code)) is False, f"SUB+viewer 不应能写 {code}"
    for code in VIEWER_READ:
        assert has_permission(user, Permission(code)) is True, f"SUB+viewer 应能读 {code}"


def test_inactive_user_denied_even_if_owner_admin():
    """停用账号：即使是 OWNER+admin 也必须拒绝（fail-closed 前置）。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, has_permission

    user = _mk_user(AccountType.OWNER, RoleEnum.ADMIN, active=False)
    for code in PRIVILEGED_WRITE[:3]:
        assert has_permission(user, Permission(code)) is False, f"停用账号仍能 {code}"


def test_superuser_bypasses_viewer_demotion():
    """记录现有优先级契约：is_superuser 早于 OWNER 判定，故 superuser+viewer 仍全权。

    这与 src/api/routes/accounts.py::_is_owner 的语义一致（superuser 视为全权主账号）。
    """
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, has_permission

    user = _mk_user(AccountType.SUB, RoleEnum.VIEWER, superuser=True)
    assert has_permission(user, Permission.KNOWLEDGE_WRITE) is True


# ============================================================================
# RBACService：check_permission / get_user_permissions 与 has_permission 一致
# ============================================================================


@pytest.mark.asyncio
async def test_rbac_service_check_permission_owner_admin_short_circuit():
    """RBACService.check_permission：OWNER+admin 在权限码解析前短路放行。

    回归背景：某路由把权限码误写成 business:metrics_read（枚举中不存在），
    Permission(...) 抛 ValueError；若没有 OWNER 前置短路，老板会被误锁 403。
    """
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import RBACService

    service = RBACService(session=MagicMock())
    owner_admin = _mk_user(AccountType.OWNER, RoleEnum.ADMIN)

    # 合法权限码
    assert await service.check_permission(owner_admin, "knowledge", "write") is True
    # 未注册的权限码（拼写错误）→ OWNER+admin 仍放行，不因枚举缺失被误锁
    assert await service.check_permission(owner_admin, "business", "metrics_read") is True


@pytest.mark.asyncio
async def test_rbac_service_check_permission_owner_viewer_denied():
    """RBACService.check_permission：OWNER+viewer 不得因账号类型短路放行。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import RBACService

    service = RBACService(session=MagicMock())
    owner_viewer = _mk_user(AccountType.OWNER, RoleEnum.VIEWER)

    assert await service.check_permission(owner_viewer, "knowledge", "write") is False
    assert await service.check_permission(owner_viewer, "business", "metrics_read") is False
    # 只读仍放行
    assert await service.check_permission(owner_viewer, "knowledge", "read") is True


@pytest.mark.asyncio
async def test_get_user_permissions_owner_admin_is_full_list():
    """OWNER+admin 的权限列表必须是全量（被修复逻辑误伤会在此暴露）。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import Permission, RBACService

    service = RBACService(session=MagicMock())
    owner_admin = _mk_user(AccountType.OWNER, RoleEnum.ADMIN)

    perms = await service.get_user_permissions(owner_admin)
    assert set(perms) == {p.value for p in Permission}, (
        f"OWNER+admin 权限列表被裁剪，缺失: "
        f"{sorted({p.value for p in Permission} - set(perms))[:5]}"
    )


@pytest.mark.asyncio
async def test_get_user_permissions_sub_user_matches_role_matrix():
    """SUB+user 的权限列表 = RoleEnum.USER 矩阵，不多不少。"""
    from src.identity.models import AccountType, RoleEnum
    from src.identity.rbac import ROLE_PERMISSIONS, RBACService

    service = RBACService(session=MagicMock())
    sub_user = _mk_user(AccountType.SUB, RoleEnum.USER)

    perms = set(await service.get_user_permissions(sub_user))
    expected = {p.value for p in ROLE_PERMISSIONS[RoleEnum.USER]}
    assert perms == expected, (
        f"SUB+user 权限列表与角色矩阵不一致，多余: {sorted(perms - expected)[:5]}，"
        f"缺失: {sorted(expected - perms)[:5]}"
    )


# ============================================================================
# HTTP 端到端：真实路由上的放行/拒绝行为必须与单元层一致
# ============================================================================


@pytest.fixture
def env_setup(tmp_path):
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "rbac_owner_regression.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"
    os.environ["DATABASE_URL"] = sync_url
    import src.api.dependencies.database as dep_db
    import src.identity.database as ident_db_mod
    dep_db._engine = None
    dep_db._async_session_factory = None
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    _dep_mod = sys.modules.get("src.api._dependencies_module")
    if _dep_mod:
        _dep_mod._lifecycle_manager = None
    yield sync_url
    dep_db._engine = None
    dep_db._async_session_factory = None
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


def _register_login(client, username, role, password="testpass123"):
    client.post("/api/v1/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "full_name": username,
        "password": password,
        "role": role,
    })
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.parametrize("role", ["admin", "user"])
def test_owner_non_viewer_http_write_memory_allowed(env_setup, role):
    """HTTP 端到端：主账号（OWNER）role=admin/user 时写入业务记忆必须 200。

    这是本回归的核心：若 has_permission 的 OWNER 分支被改坏（例如整体删除
    OWNER 短路，或误写成 `and user.role == RoleEnum.ADMIN`），
    主账号将集体失去写权限，此处立刻转红。
    """
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with TestClient(create_app()) as client:
        token = _register_login(client, f"owner_{role}", role=role)
        headers = {"Authorization": f"Bearer {token}"}

        # 前置断言：确认该账号确实是主账号（否则本用例失去意义）
        me = client.get("/api/v1/auth/me", headers=headers).json()
        assert me["account_type"] == "owner", me
        assert me["role"] == role, me

        resp = client.post("/api/v1/memory/business", headers=headers, json={
            "key": f"老板写入-{role}",
            "value": "主账号应拥有完整写权限",
        })
        assert resp.status_code == 200, (
            f"OWNER+{role} 写 /api/v1/memory/business 被拒绝，"
            f"OWNER 权限被矫枉过正: {resp.status_code} {resp.text}"
        )
        body = resp.json()
        assert body["key"] == f"老板写入-{role}"
        assert body["content"] == "主账号应拥有完整写权限"


def test_owner_viewer_http_write_memory_forbidden(env_setup):
    """HTTP 端到端：主账号被降权为 viewer 后写入必须 403（原 P0 缺口）。"""
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with TestClient(create_app()) as client:
        token = _register_login(client, "owner_viewer", role="viewer")
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/v1/auth/me", headers=headers).json()
        assert me["account_type"] == "owner", me
        assert me["role"] == "viewer", me

        resp = client.post("/api/v1/memory/business", headers=headers, json={
            "key": "越权写入",
            "value": "应被拒绝",
        })
        assert resp.status_code == 403, (
            f"OWNER+viewer 仍能写入，权限绕过未修复: {resp.status_code} {resp.text}"
        )

        # 读不受影响
        assert client.get("/api/v1/memory/overview", headers=headers).status_code == 200
        assert client.get("/api/v1/memory/items", headers=headers).status_code == 200


def test_owner_admin_http_can_delete_memory(env_setup):
    """OWNER+admin 必须能执行高危删除动作（knowledge:delete）。"""
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    with TestClient(create_app()) as client:
        token = _register_login(client, "owner_admin_del", role="admin")
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post("/api/v1/memory/business", headers=headers, json={
            "key": "待删除",
            "value": "v",
        })
        assert created.status_code == 200, created.text
        item_id = created.json()["id"]

        resp = client.delete(f"/api/v1/memory/business/{item_id}", headers=headers)
        assert resp.status_code == 200, (
            f"OWNER+admin 删除被拒绝，角色权限被误伤: {resp.status_code} {resp.text}"
        )
        assert resp.json()["ok"] is True
