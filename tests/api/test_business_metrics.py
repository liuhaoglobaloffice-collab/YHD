"""回归：GET /business/metrics 必须返回真实数据库聚合，不得 500。

实测复现：路由调用 business_service.get_metrics(...)，但 BusinessService 只有
get_domain_metrics，导致 AttributeError 500；修复后 get_metrics 返回聚合 dict。
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def env_setup(tmp_path):
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "business_metrics_test.db"
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


def _owner_token(client):
    client.post("/api/v1/auth/register", json={
        "username": "biz_owner",
        "email": "biz_owner@example.com",
        "full_name": "Biz Owner",
        "password": "testpass123",
        "role": "admin",
    })
    r = client.post("/api/v1/auth/login", json={"username": "biz_owner", "password": "testpass123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_business_metrics_aggregate_returns_200_with_real_shape(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    app = create_app()
    with TestClient(app) as client:
        token = _owner_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/v1/business/metrics", headers=headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    # 聚合视图必须包含总量字段与分域明细
    for key in (
        "domain", "total_tasks", "completed_tasks", "failed_tasks",
        "in_progress_tasks", "avg_completion_time_seconds", "success_rate",
        "by_domain",
    ):
        assert key in payload, f"missing key {key}: {payload}"
    assert payload["domain"] == "all"
    # 五个业务域全部出现在分域明细中
    assert set(payload["by_domain"].keys()) == {
        "marketing", "sales", "operations", "research", "general",
    }


def test_business_metrics_domain_filter_returns_single_domain(env_setup):
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    app = create_app()
    with TestClient(app) as client:
        token = _owner_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/v1/business/metrics?domain=sales", headers=headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["domain"] == "sales"
    assert "by_domain" not in payload
    for key in ("total_tasks", "completed_tasks", "failed_tasks", "success_rate"):
        assert key in payload
