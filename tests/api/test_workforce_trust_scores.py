"""P0-5: 动态信任评分 UI - workforce 端点返回 trust/capability/risk scores.

验收：
1. EmployeeResponse JSON schema 包含 trust_score / capability_score / risk_score。
2. from_employee(session=None) 诚实返回 None 评分（离线/空会话降级）。
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest


def _ensure_src():
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def test_employee_response_schema_contains_scores():
    """EmployeeResponse 模型必须含 trust/cap/risk 三字段（兼容旧前端不报错）。"""
    _ensure_src()
    from src.api.routes.workforce import EmployeeResponse

    schema = EmployeeResponse.model_json_schema()
    props = schema["properties"]
    for f in ("trust_score", "capability_score", "risk_score"):
        assert f in props, f"EmployeeResponse missing field: {f}"
        any_of = props[f].get("anyOf") or props[f].get("type")
        # 允许 null + number
    print("EmployeeResponse schema fields (trust/cap/risk): OK")


@pytest.mark.asyncio
async def test_from_employee_without_session_scores_none():
    """无 session 时评分诚实返回 None，不伪装 0.5 默认值。"""
    _ensure_src()
    from src.workforce.models import (
        AIEmployee,
        Department,
        Position,
        AIEmployeeStatus,
    )
    from src.api.routes.workforce import EmployeeResponse

    emp = AIEmployee(
        id=uuid4(),
        name="OfflineEmp",
        department=Department.RESEARCH,
        position=Position.MARKET_RESEARCHER,
        description="desc",
        status=AIEmployeeStatus.ACTIVE,
        owner_id=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    resp = await EmployeeResponse.from_employee(emp, session=None)
    # 诚实：未查 = None
    assert resp.trust_score is None
    assert resp.capability_score is None
    assert resp.risk_score is None
    # 基础字段仍完整
    assert resp.name == "OfflineEmp"
    assert resp.id == str(emp.id)
    print("from_employee(None) returns honest None scores: OK")
