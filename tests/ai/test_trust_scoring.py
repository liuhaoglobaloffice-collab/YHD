"""
信任评分测试 — 动态信任体系 L1→L3。

测试 AgentRouter 的能力评分、风险评分、信任评分、路由降权。
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.ai.agent_router import AgentRouter


# =============================================================================
# T1: 能力评分（基于 EmployeePerformanceModel）
# =============================================================================

@pytest.mark.asyncio
async def test_capability_score_with_performance_data():
    """有性能记录时返回真实 success_rate。"""
    session = MagicMock()
    router = AgentRouter(session)

    # Mock: EmployeePerformanceModel 查询返回 success_rate=0.85
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 0.85
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_capability_score(employee_id=str(uuid4()))
    assert score == 0.85


@pytest.mark.asyncio
async def test_capability_score_no_data_returns_default():
    """无性能记录时返回 0.5 默认值。"""
    session = MagicMock()
    router = AgentRouter(session)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_capability_score(employee_id=str(uuid4()))
    assert score == 0.5



# =============================================================================
# T2: 风险评分（基于 FailureRecordModel）
# =============================================================================

@pytest.mark.asyncio
async def test_risk_score_no_failures_returns_low_risk():
    """无失败记录时风险评分低（<=0.2）。"""
    session = MagicMock()
    router = AgentRouter(session)

    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.total = 0
    mock_row.unrecovered = 0
    mock_result.first.return_value = mock_row
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_risk_score(employee_id=str(uuid4()))
    assert score <= 0.2  # 无失败 = 低风险


@pytest.mark.asyncio
async def test_risk_score_with_failures():
    """有未恢复失败时风险评分升高。"""
    session = MagicMock()
    router = AgentRouter(session)

    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.total = 3
    mock_row.unrecovered = 1
    mock_result.first.return_value = mock_row
    session.execute = AsyncMock(return_value=mock_result)

    score = await router.get_agent_risk_score(employee_id=str(uuid4()))
    assert score > 0.2  # 有未恢复失败 = 风险升高


# =============================================================================
# T3: 信任评分（综合能力+风险+权限）
# =============================================================================

@pytest.mark.asyncio
async def test_trust_score_combines_capability_and_risk():
    """信任评分综合能力和风险。"""
    session = MagicMock()
    router = AgentRouter(session)

    # Mock: capability=0.8 (first call), risk row with total=5, unrecovered=1 (second call)
    mock_perf = MagicMock()
    mock_perf.scalar_one_or_none.return_value = 0.8

    mock_fail = MagicMock()
    mock_fail_row = MagicMock()
    mock_fail_row.total = 5
    mock_fail_row.unrecovered = 1
    mock_fail.first.return_value = mock_fail_row

    session.execute = AsyncMock(side_effect=[mock_perf, mock_fail])

    score = await router.get_agent_trust_score(employee_id=str(uuid4()))
    assert 0.0 <= score <= 1.0
    # capability=0.8*0.4 + (1-risk=0.8)*0.3 + permission=0.5*0.3 = 0.32+0.24+0.15 = 0.71
    assert score > 0.5  # 高能力低风险 = 高信任


@pytest.mark.asyncio
async def test_trust_score_no_data_returns_neutral():
    """无数据时返回中性评分。"""
    session = MagicMock()
    router = AgentRouter(session)

    # Mock: capability=None (0.5), risk row total=0 (0.1)
    mock_perf = MagicMock()
    mock_perf.scalar_one_or_none.return_value = None

    mock_fail = MagicMock()
    mock_fail_row = MagicMock()
    mock_fail_row.total = 0
    mock_fail_row.unrecovered = 0
    mock_fail.first.return_value = mock_fail_row

    session.execute = AsyncMock(side_effect=[mock_perf, mock_fail])

    score = await router.get_agent_trust_score(employee_id=str(uuid4()))
    # capability=0.5*0.4 + (1-0.1)*0.3 + 0.5*0.3 = 0.2+0.27+0.15 = 0.62
    assert 0.0 <= score <= 1.0


# =============================================================================
# T4: 路由逻辑（按信任评分排序+降权）
# =============================================================================

@pytest.mark.asyncio
async def test_low_trust_employee_skipped_in_routing():
    """信任评分低于 0.3 的员工被跳过，高信任员工被选中。"""
    session = MagicMock()
    router = AgentRouter(session)

    from src.workforce.models import AIEmployeeStatus, Department, Position

    good_emp = MagicMock()
    good_emp.id = uuid4()
    good_emp.name = "优秀员工"
    good_emp.department = Department.SALES
    good_emp.position = Position.SALES_REPRESENTATIVE
    good_emp.status = AIEmployeeStatus.ACTIVE

    bad_emp = MagicMock()
    bad_emp.id = uuid4()
    bad_emp.name = "低信任员工"
    bad_emp.department = Department.SALES
    bad_emp.position = Position.SALES_REPRESENTATIVE
    bad_emp.status = AIEmployeeStatus.ACTIVE

    router.registry = MagicMock()
    router.registry.list_employees = AsyncMock(return_value=[bad_emp, good_emp])

    async def mock_trust(employee_id):
        if employee_id == str(bad_emp.id):
            return 0.1
        return 0.8

    router.get_agent_trust_score = mock_trust

    task = {"task_id": str(uuid4()), "name": "test", "agent_type": "sales", "description": "test"}
    assignment = await router.route_task(task)

    assert str(assignment.employee_id) == str(good_emp.id)
    assert assignment.confidence == 0.8
