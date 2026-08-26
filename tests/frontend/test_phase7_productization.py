from src.ui.console import FutureConsole
from src.ui.dashboard import CEODashboard, SystemStatusCard, AIWorkerCard, BusinessOverview, RiskMonitor, ActivityTimeline
from src.ui.employees import AIEmployeeCenter, AgentCard, AgentDetails
from src.ui.workflow import TaskWorkflowConsole
from src.ui.security import SecurityAuditConsole
from src.ui.models import ModelCenter
from src.ui.metrics import MetricDashboard
from src.ui.onboarding import OnboardingWizard, DemoFlow


def test_future_console_and_dashboard_components_are_additive():
    console = FutureConsole()
    console.bootstrap()
    assert console.theme == "cyberpunk"

    dashboard = CEODashboard()
    dashboard.load()
    assert dashboard.system_status["agents"] >= 0
    assert dashboard.ai_status["provider"] == "ok"

    system_card = SystemStatusCard()
    assert system_card.render()["title"] == "System Status"

    ai_worker = AIWorkerCard()
    assert ai_worker.render()["title"] == "AI Workers"

    business_overview = BusinessOverview()
    assert business_overview.render()["title"] == "Business Overview"

    risk_monitor = RiskMonitor()
    assert risk_monitor.render()["title"] == "Risk Monitor"

    activity = ActivityTimeline()
    assert activity.render()["title"] == "Activity Timeline"


def test_employee_center_and_task_workflow_security_and_model_centers_are_available():
    employee_center = AIEmployeeCenter()
    employees = employee_center.load_agents()
    assert employees[0]["name"] == "Research Agent"

    details = AgentDetails()
    assert details.render({"name": "Supplier Risk Agent"})["name"] == "Supplier Risk Agent"

    workflow_console = TaskWorkflowConsole()
    assert workflow_console.load_task("task-1")["task_id"] == "task-1"

    security_center = SecurityAuditConsole()
    assert security_center.load_security()["security_events"] >= 0

    model_center = ModelCenter()
    assert model_center.load_providers()[0]["provider"] == "OpenAI"


def test_metrics_and_demo_flow_support_productization():
    metrics = MetricDashboard()
    metrics.record("api_latency", 12)
    assert metrics.snapshot()["api_latency"] == 12

    onboarding = OnboardingWizard()
    flow = onboarding.run()
    assert flow[0]["title"] == "Create Enterprise Space"

    demo = DemoFlow()
    demo.load_demo_data()
    assert demo.load_demo_data()["enterprise"] == "LiuHao AI OS"
