"""
测试 CEO Dashboard 模块
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.modules.ceo_dashboard_module import (
    CEODashboardModule,
    MetricType,
    DashboardSection,
    KPIMetric
)
from src.core.modules import ModuleStatus


class TestCEODashboardModule:
    """测试 CEO Dashboard 模块"""
    
    def setup_method(self):
        """每个测试方法前重置模块注册表"""
        from src.core.modules import ModuleRegistry
        registry = ModuleRegistry()
        registry._modules = {}
    
    def test_module_info(self):
        """测试模块信息"""
        module = CEODashboardModule()
        info = module.get_module_info()
        
        assert info.name == "ceo_dashboard"
        assert info.version == "1.0.0"
        assert info.provides_api is True
        assert info.provides_ui is True
        assert "dashboard.kpi_updated" in info.provides_events
        assert "dashboard.alert_triggered" in info.provides_events
        assert "dashboard.data_refreshed" in info.provides_events
    
    def test_6_core_kpis_initialized(self):
        """测试 6 个核心 KPI 是否初始化"""
        module = CEODashboardModule()
        
        # Mock EventBus
        module.event_bus = Mock()
        
        # 初始化
        context = {"config": {}}
        module.initialize(context)
        
        # 验证 6 个核心 KPI
        assert len(module.kpi_cache) == 6
        
        # 验证 KPI ID
        expected_kpis = [
            "system_health",
            "task_completion",
            "ai_utilization",
            "supplier_risk",
            "approval_response",
            "revenue_impact"
        ]
        
        for kpi_id in expected_kpis:
            assert kpi_id in module.kpi_cache
            kpi = module.kpi_cache[kpi_id]
            assert isinstance(kpi, KPIMetric)
            assert kpi.value is not None
            assert kpi.unit is not None
            assert kpi.trend in ["up", "down", "stable"]
    
    def test_module_initialization(self):
        """测试模块初始化"""
        module = CEODashboardModule()
        
        # Mock EventBus
        module.event_bus = Mock()
        
        context = {
            "config": {
                "refresh_interval": 60,
                "alert_thresholds": {
                    "system_cpu": 90,
                    "system_memory": 90
                }
            }
        }
        
        # 初始化
        result = module.initialize(context)
        
        assert result is True
        assert module.status == ModuleStatus.INITIALIZED
        assert module.refresh_interval == 60
        assert module.alert_thresholds["system_cpu"] == 90
        assert len(module.kpi_cache) == 6
    
    def test_module_lifecycle(self):
        """测试模块生命周期"""
        module = CEODashboardModule()
        
        # Mock EventBus
        module.event_bus = Mock()
        
        context = {"config": {}}
        
        # 初始化 → 启动 → 停止
        assert module.initialize(context) is True
        assert module.status == ModuleStatus.INITIALIZED
        
        assert module.start() is True
        assert module.status == ModuleStatus.RUNNING
        
        assert module.stop() is True
        assert module.status == ModuleStatus.STOPPED
    
    def test_api_routes(self):
        """测试 API 路由"""
        module = CEODashboardModule()
        routes = module.get_api_routes()
        
        assert len(routes) == 9
        
        # 检查关键路由
        paths = [r["path"] for r in routes]
        assert "/api/v1/dashboard" in paths
        assert "/api/v1/dashboard/kpis" in paths
        assert "/api/v1/dashboard/charts" in paths
        assert "/api/v1/dashboard/system" in paths
        assert "/api/v1/dashboard/business" in paths
        assert "/api/v1/dashboard/ai-team" in paths
        assert "/api/v1/dashboard/tasks" in paths
        assert "/api/v1/dashboard/alerts" in paths
        assert "/api/v1/dashboard/refresh" in paths
    
    def test_ui_components(self):
        """测试 UI 组件"""
        module = CEODashboardModule()
        components = module.get_ui_components()
        
        assert len(components) == 6
        
        # 检查组件名称
        names = [c["name"] for c in components]
        assert "CEODashboard" in names
        assert "KPICard" in names
        assert "ChartWidget" in names
        assert "AITeamMonitor" in names
        assert "TaskCenter" in names
        assert "AlertPanel" in names
    
    def test_get_kpis(self):
        """测试获取 KPI"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 获取 KPI
        result = module.get_kpis()
        
        assert "data" in result
        kpis = result["data"]
        assert len(kpis) == 6
        
        # 验证 KPI 结构
        for kpi in kpis:
            assert "id" in kpi
            assert "name" in kpi
            assert "value" in kpi
            assert "unit" in kpi
            assert "change" in kpi
            assert "trend" in kpi
            assert "timestamp" in kpi
    
    def test_get_charts(self):
        """测试获取图表"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 获取图表
        result = module.get_charts()
        
        assert "data" in result
        charts = result["data"]
        assert len(charts) == 4
        
        # 验证图表结构
        chart_ids = [c["id"] for c in charts]
        assert "task_trend" in chart_ids
        assert "ai_performance" in chart_ids
        assert "supplier_risk" in chart_ids
        assert "revenue_impact" in chart_ids
        
        # 验证图表数据
        for chart in charts:
            assert "id" in chart
            assert "name" in chart
            assert "type" in chart
            assert "data" in chart
            assert isinstance(chart["data"], list)
    
    def test_get_dashboard_data(self):
        """测试获取完整仪表板数据"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 获取完整数据
        result = module.get_dashboard_data()
        
        assert "data" in result
        data = result["data"]
        
        # 验证数据结构
        assert "timestamp" in data
        assert "kpis" in data
        assert "charts" in data
        assert "system" in data
        assert "business" in data
        assert "ai_team" in data
        assert "tasks" in data
        assert "alerts" in data
        
        # 验证子数据
        assert len(data["kpis"]) == 6
        assert len(data["charts"]) == 4
    
    def test_get_system_overview(self):
        """测试获取系统概览"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        result = module.get_system_overview()
        
        assert "data" in result
        system = result["data"]
        
        assert "status" in system
        assert "uptime_hours" in system
        assert "total_users" in system
        assert "active_sessions" in system
        assert "cpu_usage" in system
        assert "memory_usage" in system
        assert "disk_usage" in system
    
    def test_get_business_metrics(self):
        """测试获取业务指标"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        result = module.get_business_metrics()
        
        assert "data" in result
        business = result["data"]
        
        assert "total_tasks" in business
        assert "completed_tasks" in business
        assert "failed_tasks" in business
        assert "in_progress_tasks" in business
        assert "success_rate" in business
        assert "avg_completion_time_hours" in business
        assert "revenue_impact" in business
    
    def test_get_ai_team_status(self):
        """测试获取 AI 团队状态"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        result = module.get_ai_team_status()
        
        assert "data" in result
        ai_team = result["data"]
        
        assert "total_employees" in ai_team
        assert "active_employees" in ai_team
        assert "suspended_employees" in ai_team
        assert "total_tasks_completed" in ai_team
        assert "avg_tasks_per_employee" in ai_team
        assert "top_performers" in ai_team
        
        # 验证 top_performers 是列表
        assert isinstance(ai_team["top_performers"], list)
        assert len(ai_team["top_performers"]) > 0
    
    def test_get_task_center(self):
        """测试获取任务中心"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        result = module.get_task_center()
        
        assert "data" in result
        tasks = result["data"]
        
        assert "total_tasks" in tasks
        assert "pending_tasks" in tasks
        assert "running_tasks" in tasks
        assert "completed_tasks" in tasks
        assert "failed_tasks" in tasks
        assert "recent_tasks" in tasks
        
        # 验证 recent_tasks 是列表
        assert isinstance(tasks["recent_tasks"], list)
    
    def test_get_alerts(self):
        """测试获取告警"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        result = module.get_alerts()
        
        assert "data" in result
        alerts = result["data"]
        
        # 验证告警是列表
        assert isinstance(alerts, list)
        
        # 如果有告警，验证结构
        for alert in alerts:
            assert "id" in alert
            assert "level" in alert
            assert "title" in alert
            assert "message" in alert
            assert "timestamp" in alert
    
    def test_alert_threshold_cpu(self):
        """测试 CPU 告警阈值"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        # 设置低阈值触发告警
        context = {
            "config": {
                "alert_thresholds": {
                    "system_cpu": 40  # 低于实际 CPU 使用率
                }
            }
        }
        module.initialize(context)
        
        # 获取告警
        result = module.get_alerts()
        alerts = result["data"]
        
        # 应该有 CPU 告警
        cpu_alerts = [a for a in alerts if "CPU" in a["title"]]
        assert len(cpu_alerts) > 0
    
    def test_refresh_data(self):
        """测试刷新数据"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 刷新数据
        result = module.refresh_data()
        
        assert "success" in result
        assert result["success"] is True
        assert "timestamp" in result
        
        # 验证事件发布
        module.event_bus.publish.assert_called()
    
    def test_health_check(self):
        """测试健康检查"""
        module = CEODashboardModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        health = module.health_check()
        
        assert health["status"] == "healthy"
        assert "message" in health
        assert "details" in health
        assert health["details"]["kpi_count"] == 6
    
    def test_kpi_metric_structure(self):
        """测试 KPI 指标结构"""
        from datetime import datetime, UTC
        
        kpi = KPIMetric(
            id="test_kpi",
            name="Test KPI",
            value=85.5,
            unit="%",
            change=2.3,
            trend="up",
            target=90.0
        )
        
        assert kpi.id == "test_kpi"
        assert kpi.name == "Test KPI"
        assert kpi.value == 85.5
        assert kpi.unit == "%"
        assert kpi.change == 2.3
        assert kpi.trend == "up"
        assert kpi.target == 90.0
        assert kpi.timestamp is not None
    
    def test_metric_type_enum(self):
        """测试指标类型枚举"""
        assert MetricType.KPI.value == "kpi"
        assert MetricType.CHART.value == "chart"
        assert MetricType.TABLE.value == "table"
        assert MetricType.TIMELINE.value == "timeline"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.MAP.value == "map"
    
    def test_dashboard_section_enum(self):
        """测试仪表板区域枚举"""
        assert DashboardSection.SYSTEM.value == "system"
        assert DashboardSection.BUSINESS.value == "business"
        assert DashboardSection.AI_TEAM.value == "ai_team"
        assert DashboardSection.TASKS.value == "tasks"
        assert DashboardSection.APPROVALS.value == "approvals"
        assert DashboardSection.SUPPLIERS.value == "suppliers"
        assert DashboardSection.FINANCE.value == "finance"
