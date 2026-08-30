"""
经营摘要报告测试 - 阶段 3 T10。

老板长期不在线场景的最小基础：按需生成聚合报告（非离线调度），
聚合 Dashboard KPI、业务告警（scan_business_anomalies）、Goal 进度、AI 成本。

Covers:
- 报告结构完整（timestamp/kpis/alerts/goals/cost）
- 无数据时各部分如实标注"暂无"
- 有真实数据时聚合告警/目标/成本
- 数据源部分查询失败时独立降级，不影响其余部分
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.modules.ceo_dashboard_module import CEODashboardModule


def _scalar_result(value):
    """构造 scalar_one() 返回指定值的查询结果 Mock。"""
    m = MagicMock()
    m.scalar_one.return_value = value
    return m


@pytest.mark.asyncio
async def test_summary_report_structure():
    """报告结构完整。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(0))

    report = await module.generate_summary_report(session)

    for key in ("timestamp", "kpis", "alerts", "goals", "cost"):
        assert key in report, f"报告缺少 {key} 部分"
    assert report["status"] == "generated"


@pytest.mark.asyncio
async def test_summary_report_with_no_data():
    """无数据时各部分如实标注"暂无"。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(0))

    report = await module.generate_summary_report(session)

    assert report["status"] == "generated"
    assert report["goals"]["count"] == 0
    assert "暂无" in report["goals"]["message"]
    assert len(report["alerts"]["items"]) == 0
    assert "暂无" in report["alerts"]["message"]
    assert "暂无" in report["cost"]["message"]


@pytest.mark.asyncio
async def test_summary_report_aggregates_real_data():
    """有真实数据时聚合告警/目标/成本。"""
    module = CEODashboardModule()
    session = MagicMock()
    # 查询顺序: 告警扫描(本周线索, 上周线索, 流失, 高风险供应商) + Goal 数 + 成本
    session.execute = AsyncMock(side_effect=[
        _scalar_result(2),     # this_week → 与上周相比下降 80%
        _scalar_result(10),    # last_week
        _scalar_result(0),     # churn
        _scalar_result(0),     # supplier risk
        _scalar_result(3),     # goals count
        _scalar_result(12.5),  # cost total
    ])

    report = await module.generate_summary_report(session)

    # 告警聚合自 scan_business_anomalies
    assert len(report["alerts"]["items"]) == 1
    assert report["alerts"]["items"][0]["type"] == "lead_decline"
    assert "1 条告警" in report["alerts"]["message"]

    # Goal 进度
    assert report["goals"]["count"] == 3
    assert "3" in report["goals"]["message"]

    # AI 成本
    assert report["cost"]["total_usd"] == 12.5
    assert "12.50" in report["cost"]["message"]


@pytest.mark.asyncio
async def test_summary_report_partial_failure_degrades():
    """数据源部分查询失败时独立降级，不影响其余部分。

    告警扫描 4 次查询全部失败 → 告警为空但报告仍生成；
    Goal 查询失败 → 如实标注"不可用"；成本查询失败 → 如实标注"不可用"。
    """
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))

    report = await module.generate_summary_report(session)

    assert report["status"] == "generated"
    # 各部分独立降级，不崩溃
    assert "不可用" in report["alerts"]["message"]
    assert "不可用" in report["goals"]["message"]
    assert "不可用" in report["cost"]["message"]
