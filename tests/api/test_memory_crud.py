"""P1-G6.2 企业记忆统一 CRUD API：基于 EnterpriseMemory facade。

覆盖端点：
- GET  /memory/overview              双系统分级统计
- GET  /memory/items                 统一列表（origin/kind/agent_id 过滤）
- POST /memory/business              新增业务键值记忆
- DELETE /memory/business/{id}       删除业务记忆
- DELETE /memory/agent/{id}          删除会话记忆
- POST /memory/agent/{id}/core       标记核心（永久保留）

验收：
1. 未登录 -> 401
2. admin 全链路：业务记忆 创建->统一列表->统计->删除，审计真实落库
3. 会话记忆：列表(origin=agent)->标记核心->删除
4. viewer：读 200 / 写 403（权限隔离）
5. 参数校验：非法 memory_type -> 422；删除不存在 -> 404
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def env_setup(tmp_path):
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "memory_crud_test.db"
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


def _register_login(client, username, role="admin", password="testpass123"):
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


def _async_url(sync_url: str) -> str:
    return sync_url.replace("sqlite://", "sqlite+aiosqlite://", 1)


def _seed_agent_memory(sync_url: str, user_id: int, content: str = "帮我跟进德国客户") -> int:
    """直接向 agent_memories 表插入一条会话记忆，返回自增 id。"""

    async def _run():
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        import src.database.models  # noqa: F401 确保表注册
        from src.database.base import Base
        from src.database.models import AgentMemoryModel

        engine = create_async_engine(_async_url(sync_url))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            m = AgentMemoryModel(
                user_id=user_id,
                agent_id="emp-001",
                role="user",
                content=content,
                memory_level="short_term",
                importance=0.5,
            )
            session.add(m)
            await session.commit()
            await session.refresh(m)
            mid = m.id
        await engine.dispose()
        return mid

    return asyncio.run(_run())


def _count_audit_rows(sync_url: str, resource_type: str) -> int:
    """统计 audit_logs 表中指定 resource_type 的行数（验证审计真实落库）。"""

    async def _run():
        from sqlalchemy import func, select
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        import src.identity.models  # noqa: F401
        from src.database.base import Base
        from src.identity.models import AuditLog

        engine = create_async_engine(_async_url(sync_url))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            cnt = (
                await session.execute(
                    select(func.count(AuditLog.id)).where(
                        AuditLog.resource_type == resource_type
                    )
                )
            ).scalar_one()
        await engine.dispose()
        return int(cnt)

    return asyncio.run(_run())


# ============================================================================
# 认证与权限
# ============================================================================


def test_memory_overview_unauth_is_401(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/memory/overview")
    assert resp.status_code in (401, 403), resp.status_code


def test_viewer_read_ok_write_forbidden(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, "mem_viewer", role="viewer")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/memory/overview", headers=headers)
        assert resp.status_code == 200, resp.text
        resp = client.get("/api/v1/memory/items", headers=headers)
        assert resp.status_code == 200, resp.text

        resp = client.post("/api/v1/memory/business", headers=headers, json={
            "key": "越权写入",
            "value": "应被拒绝",
        })
        assert resp.status_code == 403, f"expect 403, got {resp.status_code}: {resp.text}"


# ============================================================================
# 业务键值记忆（knowledge）全链路
# ============================================================================


def test_business_memory_full_chain(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, "mem_admin")
        headers = {"Authorization": f"Bearer {token}"}

        # 创建
        resp = client.post("/api/v1/memory/business", headers=headers, json={
            "key": "发货偏好",
            "value": "默认 DHL 3日达",
            "memory_type": "long_term",
        })
        assert resp.status_code == 200, resp.text
        item = resp.json()
        assert item["origin"] == "knowledge"
        assert item["kind"] == "long_term"
        assert item["key"] == "发货偏好"
        assert item["content"] == "默认 DHL 3日达"

        # 统一列表包含新记忆
        resp = client.get("/api/v1/memory/items", headers=headers)
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        match = [i for i in items if i["id"] == item["id"]]
        assert len(match) == 1, items

        # 统计
        resp = client.get("/api/v1/memory/overview", headers=headers)
        assert resp.status_code == 200, resp.text
        stats = resp.json()
        assert stats["knowledge"]["long_term"] >= 1, stats
        assert stats["knowledge"]["total"] >= 1, stats
        assert stats["total"] >= 1, stats

        # 删除
        resp = client.delete(f"/api/v1/memory/business/{item['id']}", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True

        # 删除后列表不含
        resp = client.get("/api/v1/memory/items", headers=headers)
        items = resp.json()["items"]
        assert not any(i["id"] == item["id"] for i in items), items

    # 审计真实落库（create + delete 至少各一条 memory 审计）
    assert _count_audit_rows(env_setup, "memory") >= 2, "审计未真实落库"


def test_business_memory_delete_not_found(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, "mem_admin_nf")
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete(
            "/api/v1/memory/business/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
    assert resp.status_code == 404, f"expect 404, got {resp.status_code}: {resp.text}"


def test_business_memory_invalid_type_is_422(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, "mem_admin_val")
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/v1/memory/business", headers=headers, json={
            "key": "k",
            "value": "v",
            "memory_type": "bogus",
        })
    assert resp.status_code == 422, resp.status_code


# ============================================================================
# 会话记忆（agent）流程
# ============================================================================


def test_agent_memory_list_core_delete(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, "mem_admin_ag")
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/v1/auth/me", headers=headers).json()
        user_id = me["id"]
        mid = _seed_agent_memory(env_setup, user_id)

        # origin=agent 列表包含种子记忆
        resp = client.get("/api/v1/memory/items?origin=agent", headers=headers)
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        target = next(i for i in items if str(i["id"]) == str(mid))
        assert target["origin"] == "agent"
        assert target["key"] == "emp-001"
        assert target["content"] == "帮我跟进德国客户"

        # origin=knowledge 过滤不含 agent 记忆
        resp = client.get("/api/v1/memory/items?origin=knowledge", headers=headers)
        assert resp.status_code == 200
        assert all(i["origin"] == "knowledge" for i in resp.json()["items"])

        # 标记核心
        resp = client.post(
            f"/api/v1/memory/agent/{mid}/core", headers=headers, json={"is_core": True}
        )
        assert resp.status_code == 200, resp.text
        updated = resp.json()
        assert updated["is_core"] is True, updated

        # 删除
        resp = client.delete(f"/api/v1/memory/agent/{mid}", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True

        # 删除后 origin=agent 不含
        resp = client.get("/api/v1/memory/items?origin=agent", headers=headers)
        assert not any(
            str(i["id"]) == str(mid) for i in resp.json()["items"]
        ), resp.text


def test_agent_memory_delete_not_found(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, "mem_admin_ag_nf")
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete("/api/v1/memory/agent/999999", headers=headers)
    assert resp.status_code == 404, f"expect 404, got {resp.status_code}: {resp.text}"