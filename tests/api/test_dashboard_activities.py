"""P0-2 Dashboard 真实活动流：新增 /dashboard/activities 聚合 audit/tasks/workflows。"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
import uuid

import pytest


@pytest.fixture
def env_setup(tmp_path):
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "dashboard_activities_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    import sys
    import src.identity.database as ident_db_mod
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    _dep_mod = sys.modules.get("src.api._dependencies_module")
    if _dep_mod:
        _dep_mod._lifecycle_manager = None
    yield
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


def _seed_admin_and_login(client):
    client.post("/api/v1/auth/register", json={
        "username": "dash_admin",
        "email": "dash_admin@example.com",
        "full_name": "Dash Admin",
        "password": "testpass123",
        "role": "admin",
    })
    r = client.post("/api/v1/auth/login", json={"username": "dash_admin", "password": "testpass123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_activities_empty_db_returns_empty_list_not_demo(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    app = create_app()
    with TestClient(app) as client:
        token = _seed_admin_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/v1/dashboard/activities?limit=20", headers=headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload, list), type(payload)
    demo_ids = {"1", "2", "3", "4", "5"}
    for item in payload:
        assert str(item.get("id")) not in demo_ids, f"detect demo: {item}"


@pytest.mark.asyncio
async def test_activities_returns_mixed_and_sorted(env_setup):
    """直接调用 endpoint 函数注入数据，避免两个同步 session 读不同 db。"""
    import importlib
    from types import SimpleNamespace
    from datetime import datetime, timedelta, timezone
    import uuid

    from src.api.routes.dashboard import get_dashboard_activities
    from src.database.base import Base
    from src.identity.models import AuditLog, User, RoleEnum
    from src.database.models import (
        TaskModel,
        WorkflowExecutionModel,
        WorkflowModel,
    )
    import src.api.dependencies.database as dep_db
    import src.identity.database as ident_db_mod
    dep_db._engine = None
    dep_db._async_session_factory = None
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    from src.api.dependencies.database import get_session_factory, init_database
    _Sess = get_session_factory()
    await init_database()

    importlib.import_module("src.business.supplier.models")
    importlib.import_module("src.tasks.models")
    importlib.import_module("src.database.models")
    importlib.import_module("src.identity.models")
    importlib.import_module("src.workflow.models")

    now = datetime.now(timezone.utc)

    async with _Sess() as session:
        # Seed user
        uid = "u-" + str(uuid.uuid4())[:8]
        u = User(
            username="dash_direct",
            email="dash_direct@example.com",
            full_name="Dash Direct",
            hashed_password="x",
            role=RoleEnum.ADMIN,
            is_active=True,
        )
        session.add(u)
        await session.flush()

        audit_ts = now - timedelta(minutes=10)
        task_ts = now - timedelta(minutes=5)
        wf_ts = now

        session.add(AuditLog(
            user_id=u.id,
            action="login",
            resource_type="auth",
            resource_id=None,
            status="success",
            timestamp=audit_ts,
        ))
        session.add(TaskModel(
            id=str(uuid.uuid4()),
            title="分析东南亚市场",
            status="completed",
            priority="medium",
            task_type="data_analysis",
            creator_id=str(u.id),
            created_at=task_ts,
        ))
        wf_id = str(uuid.uuid4())
        session.add(WorkflowModel(
            id=wf_id,
            name="demo wf",
            description="test",
            version=1,
            enabled=True,
            created_by=str(u.id),
            created_at=now - timedelta(minutes=20),
            updated_at=now - timedelta(minutes=20),
            steps=[],
            context={},
            tags=[],
        ))
        await session.flush()
        session.add(WorkflowExecutionModel(
            id=str(uuid.uuid4()),
            workflow_id=wf_id,
            user_id=str(u.id),
            status="running",
            created_at=wf_ts,
            started_at=wf_ts,
            variables={},
        ))
        await session.commit()

        # 伪造 current_user / Depends 直接传参调用
        fake_user = SimpleNamespace(id=u.id, full_name=u.full_name, username=u.username)
        items = await get_dashboard_activities(limit=10, db=session, current_user=fake_user)

    assert isinstance(items, list)
    assert len(items) >= 3, f"got {len(items)}: {items}"
    for it in items:
        for k in ("id", "timestamp", "category", "actor", "action_summary", "status"):
            assert k in it, f"missing field {k}: {it}"
    ts = [it["timestamp"] for it in items]
    assert ts == sorted(ts, reverse=True), f"not desc: {ts}"
    cats = [i["category"] for i in items]
    assert "workflow" in cats and "task" in cats and "audit" in cats, cats
    wf_item = next(i for i in items if i["category"] == "workflow")
    assert wf_item["status"] == "running"
