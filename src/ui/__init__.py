"""Phase 7 additive productization and future console scaffolding."""

from .console import FutureConsole
from .dashboard import (
    CEODashboard,
    SystemStatusCard,
    AIWorkerCard,
    BusinessOverview,
    RiskMonitor,
    ActivityTimeline,
)
from .employees import AIEmployeeCenter, AgentCard, AgentDetails
from .workflow import TaskWorkflowConsole
from .security import SecurityAuditConsole
from .models import ModelCenter
from .metrics import MetricDashboard
from .onboarding import OnboardingWizard, DemoFlow

__all__ = [
    "FutureConsole",
    "CEODashboard",
    "SystemStatusCard",
    "AIWorkerCard",
    "BusinessOverview",
    "RiskMonitor",
    "ActivityTimeline",
    "AIEmployeeCenter",
    "AgentCard",
    "AgentDetails",
    "TaskWorkflowConsole",
    "SecurityAuditConsole",
    "ModelCenter",
    "MetricDashboard",
    "OnboardingWizard",
    "DemoFlow",
]
