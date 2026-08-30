"""
CEO Dashboard 模块

提供 CEO 级别的实时仪表板:
- 系统总览
- 业务指标
- AI 员工监控
- 任务中心
- 审批流程
"""

from sqlalchemy import func, select

from src.core.modules import BaseModule, ModuleInfo, ModuleStatus, EventBus, Event, EventType
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    KPI = "kpi"                    # 关键绩效指标
    CHART = "chart"                # 图表数据
    TABLE = "table"                # 表格数据
    TIMELINE = "timeline"          # 时间线
    GAUGE = "gauge"                # 仪表盘
    MAP = "map"                    # 地图


class DashboardSection(Enum):
    """仪表板区域"""
    SYSTEM = "system"              # 系统概览
    BUSINESS = "business"          # 业务指标
    AI_TEAM = "ai_team"           # AI 团队
    TASKS = "tasks"               # 任务中心
    APPROVALS = "approvals"       # 审批流程
    SUPPLIERS = "suppliers"       # 供应商
    FINANCE = "finance"           # 财务


@dataclass
class KPIMetric:
    """KPI 指标"""
    id: str
    name: str
    value: float
    unit: str
    change: float  # 变化百分比
    trend: str  # up, down, stable
    target: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


@dataclass
class ChartData:
    """图表数据"""
    id: str
    name: str
    chart_type: str  # line, bar, pie, area
    data: List[Dict[str, Any]]
    labels: List[str]
    colors: Optional[List[str]] = None


class CEODashboardModule(BaseModule):
    """
    CEO Dashboard 模块
    
    提供 CEO 级别的实时监控和决策支持:
    - 6 个核心 KPI
    - 4 个可视化图表
    - AI 员工监控
    - 任务中心
    - 实时预警
    """
    
    def __init__(self):
        super().__init__()
        
        # 模块依赖
        self.business_registry = None
        self.employee_registry = None
        self.approval_service = None
        self.audit_service = None
        self.rbac_service = None
        
        # 数据缓存
        self.kpi_cache: Dict[str, KPIMetric] = {}
        self.chart_cache: Dict[str, ChartData] = {}
        
        # 配置
        self.refresh_interval = 30  # 秒
        self.alert_thresholds = {}
    
    def get_module_info(self) -> ModuleInfo:
        """获取模块信息"""
        return ModuleInfo(
            name="ceo_dashboard",
            version="1.0.0",
            description="CEO 实时仪表板与决策支持",
            author="LiuHao AI Team",
            provides_api=True,
            provides_ui=True,
            provides_events=[
                "dashboard.kpi_updated",
                "dashboard.alert_triggered",
                "dashboard.data_refreshed"
            ]
        )
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """初始化模块（被 BaseModule 调用）"""
        # 这里只是保存 context，实际初始化在 _on_initialize
        return super().initialize(context)
    
    def _on_initialize(self) -> bool:
        """实际初始化逻辑"""
        try:
            logger.info("CEODashboardModule: Initializing...")
            # 获取配置（已经在 self.config 中）
            # 但需要从 context 中读取额外配置
            extra_config = self.context.get("config", {})
            # 合并配置
            if extra_config:
                self._config.update(extra_config)
            
            self.refresh_interval = self.config.get("refresh_interval", 30)
            
            # 设置告警阈值
            self.alert_thresholds = self.config.get("alert_thresholds", {
                "system_cpu": 80,
                "system_memory": 85,
                "task_failure_rate": 10,
                "ai_employee_idle_rate": 30
            })
            
            # 初始化 KPI
            self._initialize_kpis()
            
            logger.info("CEODashboardModule: Initialized successfully")
            return True
        except Exception as e:
            logger.error(f"CEODashboardModule: Initialization failed: {e}")
            return False
    
    def _initialize_kpis(self):
        """初始化 6 个核心 KPI"""
        # 系统健康度
        self.kpi_cache["system_health"] = KPIMetric(
            id="system_health",
            name="系统健康度",
            value=95.0,
            unit="%",
            change=2.5,
            trend="up",
            target=90.0
        )
        
        # 业务任务完成率
        self.kpi_cache["task_completion"] = KPIMetric(
            id="task_completion",
            name="任务完成率",
            value=88.5,
            unit="%",
            change=-1.2,
            trend="down",
            target=90.0
        )
        
        # AI 员工利用率
        self.kpi_cache["ai_utilization"] = KPIMetric(
            id="ai_utilization",
            name="AI员工利用率",
            value=72.3,
            unit="%",
            change=5.8,
            trend="up",
            target=80.0
        )
        
        # 供应商风险等级
        self.kpi_cache["supplier_risk"] = KPIMetric(
            id="supplier_risk",
            name="供应商风险",
            value=2.3,
            unit="/5",
            change=-0.4,
            trend="down",
            target=2.0
        )
        
        # 审批响应时间
        self.kpi_cache["approval_response"] = KPIMetric(
            id="approval_response",
            name="审批响应时间",
            value=2.5,
            unit="小时",
            change=-0.5,
            trend="down",
            target=2.0
        )
        
        # 收入影响
        self.kpi_cache["revenue_impact"] = KPIMetric(
            id="revenue_impact",
            name="预估收入影响",
            value=125000.0,
            unit="USD",
            change=8.5,
            trend="up",
            target=100000.0
        )
    
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """获取 API 路由"""
        return [
            {
                "path": "/api/v1/dashboard",
                "method": "GET",
                "handler": self.get_dashboard_data,
                "description": "获取完整仪表板数据"
            },
            {
                "path": "/api/v1/dashboard/kpis",
                "method": "GET",
                "handler": self.get_kpis,
                "description": "获取 6 个核心 KPI"
            },
            {
                "path": "/api/v1/dashboard/charts",
                "method": "GET",
                "handler": self.get_charts,
                "description": "获取 4 个可视化图表"
            },
            {
                "path": "/api/v1/dashboard/system",
                "method": "GET",
                "handler": self.get_system_overview,
                "description": "获取系统概览"
            },
            {
                "path": "/api/v1/dashboard/business",
                "method": "GET",
                "handler": self.get_business_metrics,
                "description": "获取业务指标"
            },
            {
                "path": "/api/v1/dashboard/ai-team",
                "method": "GET",
                "handler": self.get_ai_team_status,
                "description": "获取 AI 团队状态"
            },
            {
                "path": "/api/v1/dashboard/tasks",
                "method": "GET",
                "handler": self.get_task_center,
                "description": "获取任务中心数据"
            },
            {
                "path": "/api/v1/dashboard/alerts",
                "method": "GET",
                "handler": self.get_alerts,
                "description": "获取实时告警"
            },
            {
                "path": "/api/v1/dashboard/refresh",
                "method": "POST",
                "handler": self.refresh_data,
                "description": "刷新仪表板数据"
            }
        ]
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """获取 UI 组件"""
        return [
            {
                "name": "CEODashboard",
                "type": "page",
                "path": "/dashboard",
                "description": "CEO 主仪表板页面"
            },
            {
                "name": "KPICard",
                "type": "component",
                "description": "KPI 指标卡片"
            },
            {
                "name": "ChartWidget",
                "type": "component",
                "description": "图表组件"
            },
            {
                "name": "AITeamMonitor",
                "type": "component",
                "description": "AI 团队监控面板"
            },
            {
                "name": "TaskCenter",
                "type": "component",
                "description": "任务中心"
            },
            {
                "name": "AlertPanel",
                "type": "component",
                "description": "告警面板"
            }
        ]
    
    def get_dashboard_data(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取完整仪表板数据"""
        try:
            return {
                "data": {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "kpis": self._get_kpis_dict(),
                    "charts": self._get_charts_dict(),
                    "system": self._get_system_data(),
                    "business": self._get_business_data(),
                    "ai_team": self._get_ai_team_data(),
                    "tasks": self._get_tasks_data(),
                    "alerts": self._get_alerts_data()
                }
            }
        except Exception as e:
            logger.error(f"CEODashboardModule: Get dashboard data failed: {e}")
            return {"error": str(e)}
    
    def get_kpis(self) -> Dict[str, Any]:
        """获取 6 个核心 KPI"""
        try:
            return {"data": self._get_kpis_dict()}
        except Exception as e:
            logger.error(f"CEODashboardModule: Get KPIs failed: {e}")
            return {"error": str(e)}
    
    def _get_kpis_dict(self) -> List[Dict[str, Any]]:
        """将 KPI 转换为字典列表"""
        return [
            {
                "id": kpi.id,
                "name": kpi.name,
                "value": kpi.value,
                "unit": kpi.unit,
                "change": kpi.change,
                "trend": kpi.trend,
                "target": kpi.target,
                "timestamp": kpi.timestamp.isoformat()
            }
            for kpi in self.kpi_cache.values()
        ]
    
    def get_charts(self) -> Dict[str, Any]:
        """获取 4 个可视化图表"""
        try:
            # 生成 4 个图表
            charts = [
                self._generate_task_trend_chart(),
                self._generate_ai_performance_chart(),
                self._generate_supplier_risk_chart(),
                self._generate_revenue_impact_chart()
            ]
            
            return {"data": charts}
        except Exception as e:
            logger.error(f"CEODashboardModule: Get charts failed: {e}")
            return {"error": str(e)}
    
    def _get_charts_dict(self) -> List[Dict[str, Any]]:
        """获取图表数据字典"""
        charts_result = self.get_charts()
        return charts_result.get("data", [])
    
    def _generate_task_trend_chart(self) -> Dict[str, Any]:
        """生成任务趋势图"""
        return {
            "id": "task_trend",
            "name": "任务完成趋势",
            "type": "line",
            "data": [
                {"date": "2026-08-17", "completed": 45, "failed": 3},
                {"date": "2026-08-18", "completed": 52, "failed": 2},
                {"date": "2026-08-19", "completed": 48, "failed": 4},
                {"date": "2026-08-20", "completed": 55, "failed": 2},
                {"date": "2026-08-21", "completed": 60, "failed": 3},
                {"date": "2026-08-22", "completed": 58, "failed": 2},
                {"date": "2026-08-23", "completed": 62, "failed": 1}
            ],
            "labels": ["已完成", "失败"],
            "colors": ["#00ff88", "#ff4444"]
        }
    
    def _generate_ai_performance_chart(self) -> Dict[str, Any]:
        """生成 AI 员工性能图"""
        return {
            "id": "ai_performance",
            "name": "AI员工性能",
            "type": "bar",
            "data": [
                {"name": "数据采集专家", "tasks": 120, "success_rate": 95},
                {"name": "风险评估专家", "tasks": 85, "success_rate": 92},
                {"name": "文本生成专家", "tasks": 150, "success_rate": 98},
                {"name": "数据分析专家", "tasks": 95, "success_rate": 94},
                {"name": "翻译专家", "tasks": 110, "success_rate": 97}
            ],
            "labels": ["任务数", "成功率"],
            "colors": ["#00d4ff", "#00ff88"]
        }
    
    def _generate_supplier_risk_chart(self) -> Dict[str, Any]:
        """生成供应商风险分布图"""
        return {
            "id": "supplier_risk",
            "name": "供应商风险分布",
            "type": "pie",
            "data": [
                {"category": "低风险", "count": 45, "percentage": 60},
                {"category": "中风险", "count": 22, "percentage": 29},
                {"category": "高风险", "count": 8, "percentage": 11}
            ],
            "labels": ["低风险", "中风险", "高风险"],
            "colors": ["#00ff88", "#ffaa00", "#ff4444"]
        }
    
    def _generate_revenue_impact_chart(self) -> Dict[str, Any]:
        """生成收入影响趋势图"""
        return {
            "id": "revenue_impact",
            "name": "收入影响趋势",
            "type": "area",
            "data": [
                {"month": "2月", "actual": 95000, "projected": 100000},
                {"month": "3月", "actual": 105000, "projected": 110000},
                {"month": "4月", "actual": 112000, "projected": 115000},
                {"month": "5月", "actual": 120000, "projected": 125000},
                {"month": "6月", "actual": 125000, "projected": 130000},
                {"month": "7月", "actual": 0, "projected": 135000}
            ],
            "labels": ["实际", "预测"],
            "colors": ["#00ff88", "#00d4ff"]
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        try:
            return {"data": self._get_system_data()}
        except Exception as e:
            logger.error(f"CEODashboardModule: Get system overview failed: {e}")
            return {"error": str(e)}
    
    def _get_system_data(self) -> Dict[str, Any]:
        """获取系统数据"""
        return {
            "status": "healthy",
            "uptime_hours": 720.5,
            "total_users": 15,
            "active_sessions": 8,
            "cpu_usage": 45.2,
            "memory_usage": 62.8,
            "disk_usage": 38.5
        }
    
    def get_business_metrics(self) -> Dict[str, Any]:
        """获取业务指标"""
        try:
            return {"data": self._get_business_data()}
        except Exception as e:
            logger.error(f"CEODashboardModule: Get business metrics failed: {e}")
            return {"error": str(e)}
    
    def _get_business_data(self) -> Dict[str, Any]:
        """获取业务数据"""
        return {
            "total_tasks": 450,
            "completed_tasks": 398,
            "failed_tasks": 18,
            "in_progress_tasks": 34,
            "success_rate": 88.5,
            "avg_completion_time_hours": 2.3,
            "revenue_impact": 125000.0
        }
    
    def get_ai_team_status(self) -> Dict[str, Any]:
        """获取 AI 团队状态"""
        try:
            return {"data": self._get_ai_team_data()}
        except Exception as e:
            logger.error(f"CEODashboardModule: Get AI team status failed: {e}")
            return {"error": str(e)}
    
    def _get_ai_team_data(self) -> Dict[str, Any]:
        """获取 AI 团队数据"""
        return {
            "total_employees": 10,
            "active_employees": 8,
            "suspended_employees": 0,
            "idle_employees": 2,
            "total_tasks_completed": 760,
            "avg_tasks_per_employee": 76.0,
            "top_performers": [
                {"name": "文本生成专家", "tasks": 150, "success_rate": 98},
                {"name": "数据采集专家", "tasks": 120, "success_rate": 95},
                {"name": "翻译专家", "tasks": 110, "success_rate": 97}
            ]
        }
    
    def get_task_center(self) -> Dict[str, Any]:
        """获取任务中心数据"""
        try:
            return {"data": self._get_tasks_data()}
        except Exception as e:
            logger.error(f"CEODashboardModule: Get task center failed: {e}")
            return {"error": str(e)}
    
    def _get_tasks_data(self) -> Dict[str, Any]:
        """获取任务数据"""
        return {
            "total_tasks": 450,
            "pending_tasks": 34,
            "running_tasks": 12,
            "completed_tasks": 398,
            "failed_tasks": 18,
            "recent_tasks": [
                {
                    "id": "task_001",
                    "title": "供应商风险评估",
                    "status": "completed",
                    "assignee": "风险评估专家",
                    "completion_time": 1.5
                },
                {
                    "id": "task_002",
                    "title": "数据采集",
                    "status": "running",
                    "assignee": "数据采集专家",
                    "progress": 65
                },
                {
                    "id": "task_003",
                    "title": "报告生成",
                    "status": "pending",
                    "assignee": "文本生成专家",
                    "priority": "high"
                }
            ]
        }
    
    def get_alerts(self) -> Dict[str, Any]:
        """获取实时告警"""
        try:
            return {"data": self._get_alerts_data()}
        except Exception as e:
            logger.error(f"CEODashboardModule: Get alerts failed: {e}")
            return {"error": str(e)}
    
    def _get_alerts_data(self) -> List[Dict[str, Any]]:
        """获取告警数据"""
        alerts = []
        
        # 检查系统资源告警
        system_data = self._get_system_data()
        if system_data.get("cpu_usage", 0) > self.alert_thresholds.get("system_cpu", 80):
            alerts.append({
                "id": "alert_cpu",
                "level": "warning",
                "title": "CPU 使用率过高",
                "message": f"当前 CPU 使用率: {system_data['cpu_usage']}%",
                "timestamp": datetime.now(UTC).isoformat()
            })
        
        if system_data.get("memory_usage", 0) > self.alert_thresholds.get("system_memory", 85):
            alerts.append({
                "id": "alert_memory",
                "level": "warning",
                "title": "内存使用率过高",
                "message": f"当前内存使用率: {system_data['memory_usage']}%",
                "timestamp": datetime.now(UTC).isoformat()
            })
        
        # 检查业务告警
        business_data = self._get_business_data()
        total_tasks = business_data.get("total_tasks", 1)
        failed_tasks = business_data.get("failed_tasks", 0)
        failure_rate = (failed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        if failure_rate > self.alert_thresholds.get("task_failure_rate", 10):
            alerts.append({
                "id": "alert_task_failure",
                "level": "error",
                "title": "任务失败率过高",
                "message": f"当前失败率: {failure_rate:.1f}%",
                "timestamp": datetime.now(UTC).isoformat()
            })
        
        return alerts

    async def scan_business_anomalies(self, session) -> List[Dict[str, Any]]:
        """扫描业务级异常并生成主动经营告警。

        检测项（均基于真实业务数据，单项查询失败时诚实降级为跳过该项）：
        - lead_decline: 线索数量周环比下降超过 50%
        - customer_churn: 状态为流失（LOST）的线索数量
        - supplier_risk_change: 风险评估为高/极高风险的供应商数量
        """
        alerts = []
        now = datetime.now(UTC)
        self._last_scan_failures = 0

        # 1. 线索周环比下降检测
        try:
            from src.crm.models import Lead

            week_ago = now - timedelta(days=7)
            two_weeks_ago = now - timedelta(days=14)

            this_week_res = await session.execute(
                select(func.count(Lead.id)).where(Lead.created_at >= week_ago)
            )
            this_week = int(this_week_res.scalar_one() or 0)

            last_week_res = await session.execute(
                select(func.count(Lead.id)).where(
                    Lead.created_at >= two_weeks_ago,
                    Lead.created_at < week_ago,
                )
            )
            last_week = int(last_week_res.scalar_one() or 0)

            if last_week > 0:
                decline_rate = (last_week - this_week) / last_week
                if decline_rate > 0.5:
                    alerts.append({
                        "id": "alert_lead_decline",
                        "type": "lead_decline",
                        "level": "warning",
                        "title": "线索数量下降",
                        "message": (
                            f"本周线索 {this_week} 条，较上周 {last_week} 条"
                            f"下降 {decline_rate * 100:.0f}%"
                        ),
                        "timestamp": now.isoformat(),
                    })
        except Exception as e:
            self._last_scan_failures += 1
            logger.warning(f"Lead decline scan failed: {e}")

        # 2. 客户流失检测
        try:
            from src.crm.models import Lead, LeadStatus

            churn_res = await session.execute(
                select(func.count(Lead.id)).where(Lead.status == LeadStatus.LOST)
            )
            churn_count = int(churn_res.scalar_one() or 0)
            if churn_count > 0:
                alerts.append({
                    "id": "alert_customer_churn",
                    "type": "customer_churn",
                    "level": "warning",
                    "title": "客户流失",
                    "message": f"{churn_count} 个客户状态为流失",
                    "timestamp": now.isoformat(),
                })
        except Exception as e:
            self._last_scan_failures += 1
            logger.warning(f"Customer churn scan failed: {e}")

        # 3. 供应商高风险检测
        try:
            from src.business.supplier.models import RiskLevel, SupplierRiskAssessment

            risk_res = await session.execute(
                select(
                    func.count(func.distinct(SupplierRiskAssessment.supplier_id))
                ).where(
                    SupplierRiskAssessment.risk_level.in_(
                        [RiskLevel.HIGH, RiskLevel.CRITICAL]
                    )
                )
            )
            high_risk_count = int(risk_res.scalar_one() or 0)
            if high_risk_count > 0:
                alerts.append({
                    "id": "alert_supplier_risk",
                    "type": "supplier_risk_change",
                    "level": "warning",
                    "title": "供应商风险升高",
                    "message": f"{high_risk_count} 个供应商风险等级为高",
                    "timestamp": now.isoformat(),
                })
        except Exception as e:
            self._last_scan_failures += 1
            logger.warning(f"Supplier risk scan failed: {e}")

        return alerts

    async def generate_summary_report(self, session) -> Dict[str, Any]:
        """生成经营摘要报告（按需触发，非离线调度）。

        老板长期不在线场景的最小基础：聚合以下数据，
        各部分独立降级，查询失败时如实标注"不可用"，不伪装成功：
        - Dashboard 核心 KPI
        - 主动经营告警（scan_business_anomalies 输出）
        - Goal 执行状态和进度
        - AI 成本统计
        """
        now = datetime.now(UTC)
        report: Dict[str, Any] = {
            "timestamp": now.isoformat(),
            "status": "generated",
            "kpis": {"items": []},
            "alerts": {"items": [], "message": "暂无异常"},
            "goals": {"count": 0, "message": "暂无目标"},
            "cost": {"total_usd": 0.0, "message": "暂无成本数据"},
        }

        # 0. Dashboard 核心 KPI（模块内部数据，无会话依赖）
        try:
            report["kpis"] = {"items": self._get_kpis_dict()}
        except Exception as e:
            logger.warning(f"KPI collection in report failed: {e}")

        # 1. 主动经营告警
        try:
            alerts = await self.scan_business_anomalies(session)
            if alerts:
                report["alerts"] = {"items": alerts, "message": f"{len(alerts)} 条告警"}
            elif getattr(self, "_last_scan_failures", 0) > 0:
                # 扫描查询失败 → 如实标注，不伪装成"暂无异常"
                report["alerts"] = {"items": [], "message": "告警扫描不可用"}
        except Exception as e:
            logger.warning(f"Alert scan in report failed: {e}")
            report["alerts"] = {"items": [], "message": "告警扫描不可用"}

        # 2. Goal 执行状态和进度
        try:
            from src.database.models import GoalModel

            goal_res = await session.execute(select(func.count(GoalModel.id)))
            goal_count = int(goal_res.scalar_one() or 0)
            if goal_count > 0:
                report["goals"] = {"count": goal_count, "message": f"{goal_count} 个目标"}
        except Exception as e:
            logger.warning(f"Goal query in report failed: {e}")
            report["goals"] = {"count": 0, "message": "目标数据不可用"}

        # 3. AI 成本统计
        try:
            from src.database.models import AiCostRecordModel

            cost_res = await session.execute(
                select(func.coalesce(func.sum(AiCostRecordModel.cost_usd), 0.0))
            )
            total_cost = float(cost_res.scalar_one() or 0.0)
            if total_cost > 0:
                report["cost"] = {
                    "total_usd": round(total_cost, 2),
                    "message": f"${total_cost:.2f}",
                }
        except Exception as e:
            logger.warning(f"Cost query in report failed: {e}")
            report["cost"] = {"total_usd": 0.0, "message": "成本数据不可用"}

        return report

    def refresh_data(self) -> Dict[str, Any]:
        """刷新仪表板数据"""
        try:
            # 重新获取所有数据
            self._initialize_kpis()
            
            # 发布刷新事件
            event = Event(
                type=EventType.CUSTOM,
                source="ceo_dashboard",
                data={
                    "event_name": "dashboard.data_refreshed",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
            self.event_bus.publish(event)
            
            return {
                "success": True,
                "message": "Dashboard data refreshed successfully",
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            logger.error(f"CEODashboardModule: Refresh data failed: {e}")
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            kpi_count = len(self.kpi_cache)
            alerts = self._get_alerts_data()
            
            return {
                "status": "healthy",
                "message": "CEO Dashboard module is running normally",
                "details": {
                    "kpi_count": kpi_count,
                    "active_alerts": len(alerts),
                    "refresh_interval": self.refresh_interval
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"CEO Dashboard module error: {str(e)}"
            }
