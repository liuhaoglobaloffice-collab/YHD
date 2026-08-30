"""P0-4 CEO 总结报告 API：GET /ceo/summary-report。

验收：
1. 未登录/非 admin → 401/403
2. admin → 200，响应包含 status / period_days / generated_at / report.{kpis,alerts,goals,cost}
3. 非 admin 普通用户 → 403（权限隔离）
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def env_setup(tmp_path):
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "ceo_summary_report.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    import sys
    import src.api.dependencies.database as dep_db
    import src.identity.database as ident_db_mod
    dep_db._engine = None
    dep_db._async_session_factory = None
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    _dep_mod = sys.modules.get("src.api._dependencies_module")
    if _dep_mod:
        _dep_mod._lifecycle_manager = None
    yield
    dep_db._engine = None
    dep_db._async_session_factory = None
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


def _register_login(client, username="ceo_admin_x", role="admin", password="testpass123"):
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


def test_summary_report_unauth_is_401(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/ceo/summary-report")
    assert resp.status_code in (401, 403), resp.status_code


def test_summary_report_regular_user_403(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, username="ceo_user", role="viewer")
        resp = client.get("/api/v1/ceo/summary-report", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403, f"expect 403, got {resp.status_code}: {resp.text}"


def test_summary_report_admin_200_shape(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    with TestClient(create_app()) as client:
        token = _register_login(client, username="ceo_admin", role="admin")
        resp = client.get(
            "/api/v1/ceo/summary-report?period_days=7",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "generated", body
    assert "period_days" in body
    assert "generated_at" in body
    report = body["report"]
    for k in ("kpis", "alerts", "goals", "cost"):
        assert k in report, f"missing report.{k}: {report}"
