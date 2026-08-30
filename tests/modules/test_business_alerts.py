"""
业务级异常扫描测试 - 阶段 1 T5（补做），为阶段 3 T10 摘要报告提供告警输入。

Covers:
- 无数据时返回空告警列表
- 线索周环比下降超 50% 生成 lead_decline 告警
- 存在流失（LOST）线索时生成 customer_churn 告警
- 存在高/极高风险评估供应商时生成 supplier_risk_change 告警
- 查询失败时诚实降级（跳过该项，不崩溃）
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
async def test_business_anomalies_no_data_returns_empty():
    """无数据时返回空告警列表。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(0))

    alerts = await module.scan_business_anomalies(session)
    assert alerts == []


@pytest.mark.asyncio
async def test_business_anomalies_lead_decline():
    """线索周环比下降超 50% 时生成 lead_decline 告警。"""
    module = CEODashboardModule()
    session = MagicMock()
    # 查询顺序: 本周线索, 上周线索, 流失线索, 高风险供应商
    session.execute = AsyncMock(side_effect=[
        _scalar_result(2),    # this_week
        _scalar_result(10),   # last_week → 下降 80%
        _scalar_result(0),    # churn
        _scalar_result(0),    # supplier risk
    ])

    alerts = await module.scan_business_anomalies(session)
    lead_alerts = [a for a in alerts if a["type"] == "lead_decline"]
    assert len(lead_alerts) == 1
    assert lead_alerts[0]["level"] == "warning"
    assert "80%" in lead_alerts[0]["message"]


@pytest.mark.asyncio
async def test_business_anomalies_customer_churn():
    """存在流失线索时生成 customer_churn 告警。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _scalar_result(0),   # this_week
        _scalar_result(0),   # last_week → 无下降
        _scalar_result(3),   # churn → 3 个流失
        _scalar_result(0),   # supplier risk
    ])

    alerts = await module.scan_business_anomalies(session)
    churn_alerts = [a for a in alerts if a["type"] == "customer_churn"]
    assert len(churn_alerts) == 1
    assert churn_alerts[0]["level"] == "warning"
    assert "3" in churn_alerts[0]["message"]


@pytest.mark.asyncio
async def test_business_anomalies_supplier_risk():
    """存在高风险评估供应商时生成 supplier_risk_change 告警。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _scalar_result(0),   # this_week
        _scalar_result(0),   # last_week
        _scalar_result(0),   # churn
        _scalar_result(2),   # supplier risk → 2 个高风险供应商
    ])

    alerts = await module.scan_business_anomalies(session)
    risk_alerts = [a for a in alerts if a["type"] == "supplier_risk_change"]
    assert len(risk_alerts) == 1
    assert risk_alerts[0]["level"] == "warning"
    assert "2" in risk_alerts[0]["message"]


@pytest.mark.asyncio
async def test_business_anomalies_query_failure_degrades():
    """查询失败时诚实降级：跳过该项，不抛异常。"""
    module = CEODashboardModule()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))

    alerts = await module.scan_business_anomalies(session)
    assert alerts == []
