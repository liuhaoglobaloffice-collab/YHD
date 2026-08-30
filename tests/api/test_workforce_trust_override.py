"""P1-G2.2: AI 员工手动干预能力验收。

蓝图要求：老板可以对 AI 员工手动调权（信任 override / 恢复）与暂停 / 恢复。
验收：
1. set_trust_override 持久化写入 ai_employees.meta（不新建表），含 override_source=MANUAL。
2. get_agent_trust_score 优先返回 override 值（手动值覆盖动态计算）。
3. clear_trust_override 清除后恢复动态计算。
4. suspend/resume 切换 status 并持久化。
5. 诚实底线：override 数据含 actor/reason/set_at，可追溯；score 越界被拒绝。
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


def _src():
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


@pytest.mark.asyncio
async def test_set_trust_override_persists_to_meta():
    """override 写入 ai_employees.meta 并 commit。"""
    _src()
    from src.ai.agent_router import AgentRouter

    session = MagicMock()
    emp = MagicMock()
    emp.meta = {}
    session.get = AsyncMock(return_value=emp)
    session.commit = AsyncMock()

    router = AgentRouter(session)
    await router.set_trust_override(
        employee_id="emp-1", score=0.9, reason="连续3次任务成功", actor_id=42
    )

    assert session.get.called
    ov = emp.meta["trust_override"]
    assert ov["score"] == 0.9
    assert ov["reason"] == "连续3次任务成功"
    assert ov["override_source"] == "MANUAL"
    assert ov["actor_id"] == 42
    assert "set_at" in ov
    assert session.commit.called


@pytest.mark.asyncio
async def test_set_trust_override_invalid_score_rejected():
    """score 必须在 [0,1] 区间，越界抛 ValueError（fail-closed）。"""
    _src()
    from src.ai.agent_router import AgentRouter

    router = AgentRouter(MagicMock())
    with pytest.raises(ValueError):
        await router.set_trust_override("emp-1", score=1.5, reason="x", actor_id=1)
    with pytest.raises(ValueError):
        await router.set_trust_override("emp-1", score=-0.1, reason="x", actor_id=1)


@pytest.mark.asyncio
async def test_get_trust_score_respects_override():
    """有 override 时直接返回手动值，优先于动态计算。"""
    _src()
    from src.ai.agent_router import AgentRouter

    session = MagicMock()
    emp = MagicMock()
    emp.meta = {"trust_override": {"score": 0.95, "override_source": "MANUAL"}}
    session.get = AsyncMock(return_value=emp)

    router = AgentRouter(session)
    score = await router.get_agent_trust_score("emp-1")
    assert score == 0.95


@pytest.mark.asyncio
async def test_clear_trust_override_restores_dynamic():
    """清除 override 后恢复动态计算路径。"""
    _src()
    from src.ai.agent_router import AgentRouter

    session = MagicMock()
    emp = MagicMock()
    emp.meta = {"trust_override": {"score": 0.95}}
    session.get = AsyncMock(return_value=emp)
    session.commit = AsyncMock()

    router = AgentRouter(session)
    await router.clear_trust_override("emp-1")
    assert "trust_override" not in emp.meta
    assert session.commit.called


@pytest.mark.asyncio
async def test_get_trust_score_override_lookup_failure_falls_back_dynamic():
    """meta 查询异常时诚实降级到动态计算，不抛错阻塞路由。"""
    _src()
    from src.ai.agent_router import AgentRouter

    session = MagicMock()
    session.get = AsyncMock(side_effect=Exception("db down"))

    router = AgentRouter(session)
    # 不抛异常；返回动态计算值（内部会查 performance -> 0.5 默认 -> trust ≈ 0.55）
    score = await router.get_agent_trust_score("emp-1")
    assert 0.0 <= score <= 1.0


# ==================================================================
# P1-G2.2 API 层：手动干预端点（suspend / resume / trust-override）
# ==================================================================


@pytest.mark.asyncio
async def test_api_trust_override_endpoint_invokes_router():
    """POST /workforce/employees/{id}/trust-override 调用 AgentRouter 并返回 override。"""
    _src()
    from types import SimpleNamespace
    from uuid import uuid4

    from src.api.routes import workforce as wf

    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    user = SimpleNamespace(id=1)

    captured = {}

    class _FakeRouter:
        async def set_trust_override(self, employee_id, score, reason, actor_id):
            captured.update(
                employee_id=employee_id, score=score, reason=reason, actor_id=actor_id
            )
            return {"score": score, "override_source": "MANUAL", "reason": reason}

    router_instance = _FakeRouter()

    import unittest.mock as um
    with um.patch.object(wf, "AgentRouter", return_value=router_instance):
        resp = await wf.trust_override_endpoint(
            employee_id=uuid4(),
            body={"score": 0.8, "reason": "manual test"},
            session=session,
            current_user=user,
        )

    assert resp["override"]["score"] == 0.8
    assert captured["score"] == 0.8
    assert captured["actor_id"] == 1


@pytest.mark.asyncio
async def test_api_trust_override_invalid_score_400():
    """score 越界时端点返回 400（fail-closed，不写库）。"""
    _src()
    from types import SimpleNamespace
    from uuid import uuid4

    from fastapi import HTTPException

    from src.api.routes import workforce as wf

    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    user = SimpleNamespace(id=1)

    router_instance = MagicMock()
    router_instance.set_trust_override = AsyncMock(
        side_effect=ValueError("must be in [0,1]")
    )

    import unittest.mock as um
    with um.patch.object(wf, "AgentRouter", return_value=router_instance):
        with pytest.raises(HTTPException) as exc:
            await wf.trust_override_endpoint(
                employee_id=uuid4(),
                body={"score": 1.5, "reason": "x"},
                session=session,
                current_user=user,
            )
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_api_suspend_and_resume_use_service():
    """suspend/resume 端点调用 employee_service.update_employee 切换状态。"""
    _src()
    from types import SimpleNamespace
    from uuid import uuid4

    from src.api.routes import workforce as wf
    from src.workforce.models import AIEmployeeStatus, Department, Position

    user = SimpleNamespace(id=1)
    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    emp = MagicMock()
    emp.id = uuid4()
    emp.name = f"emp-{uuid4().hex[:8]}"
    emp.department = Department.OPERATIONS
    emp.position = Position.TASK_MANAGER
    emp.description = ""
    emp.agent_type = None
    emp.created_at = datetime.now(UTC)
    emp.updated_at = datetime.now(UTC)
    emp.status = AIEmployeeStatus.SUSPENDED
    service = MagicMock()
    service.update_employee = AsyncMock(return_value=emp)

    # suspend
    await wf.suspend_employee(
        employee_id=emp.id,
        employee_service=service,
        session=session,
        current_user=user,
    )
    assert service.update_employee.call_args.kwargs["status"] == AIEmployeeStatus.SUSPENDED

    # resume
    emp2 = MagicMock()
    emp2.id = emp.id
    emp2.name = emp.name
    emp2.department = Department.OPERATIONS
    emp2.position = Position.TASK_MANAGER
    emp2.description = ""
    emp2.agent_type = None
    emp2.created_at = datetime.now(UTC)
    emp2.updated_at = datetime.now(UTC)
    emp2.status = AIEmployeeStatus.ACTIVE
    service.update_employee = AsyncMock(return_value=emp2)
    await wf.resume_employee(
        employee_id=emp.id,
        employee_service=service,
        session=session,
        current_user=user,
    )
    assert service.update_employee.call_args.kwargs["status"] == AIEmployeeStatus.ACTIVE
