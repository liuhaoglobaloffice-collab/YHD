"""
CEO Dashboard Data Models

Defines Pydantic models for CEO-level views and metrics.
"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class SystemOverview(BaseModel):
    """
    System-level overview for CEO.

    Provides high-level system health and infrastructure metrics.
    """

    status: str = Field(..., description="System status: healthy, degraded, down")
    uptime_hours: float = Field(..., description="System uptime in hours")
    total_users: int = Field(..., description="Total registered users")
    active_sessions: int = Field(..., description="Currently active sessions")
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    memory_usage_percent: float = Field(..., description="Memory usage percentage")
    disk_usage_percent: float = Field(..., description="Disk usage percentage")


class BusinessOverview(BaseModel):
    """
    Business operations overview for CEO.

    Aggregates metrics across all business tasks and domains.
    """

    total_tasks: int = Field(..., description="Total business tasks")
    completed_tasks: int = Field(..., description="Completed tasks")
    failed_tasks: int = Field(..., description="Failed tasks")
    in_progress_tasks: int = Field(..., description="Tasks in progress")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_completion_time_hours: float = Field(..., description="Average completion time in hours")
    revenue_impact: float = Field(..., description="Estimated revenue impact in USD")
    total_goals: int = Field(0, description="Total goals")
    active_goals: int = Field(0, description="Active goals")
    completed_goals: int = Field(0, description="Completed goals")
    failed_goals: int = Field(0, description="Failed goals")
    total_failure_records: int = Field(0, description="Total failure records")


class AITeamOverview(BaseModel):
    """
    AI workforce overview for CEO.

    Provides metrics on AI employee performance and utilization.
    """

    total_employees: int = Field(..., description="Total AI employees")
    active_employees: int = Field(..., description="Active AI employees")
    suspended_employees: int = Field(..., description="Suspended AI employees")
    total_tasks_completed: int = Field(..., description="Total tasks completed by all employees")
    avg_tasks_per_employee: float = Field(..., description="Average tasks per employee")
    top_performers: List[Dict[str, Any]] = Field(
        default_factory=list, description="Top performing employees"
    )


class TaskOverview(BaseModel):
    """
    Task & workflow overview for CEO.

    Aggregates task execution and workflow metrics.
    """

    total_tasks: int = Field(..., description="Total tasks")
    pending_tasks: int = Field(..., description="Pending tasks")
    running_tasks: int = Field(..., description="Running tasks")
    completed_tasks: int = Field(..., description="Completed tasks")
    failed_tasks: int = Field(..., description="Failed tasks")


class ApprovalOverview(BaseModel):
    """
    Approval & governance overview for CEO.

    Provides metrics on approval requests and governance.
    """

    total_requests: int = Field(..., description="Total approval requests")
    pending_requests: int = Field(..., description="Pending approval requests")
    approved_requests: int = Field(..., description="Approved requests")
    rejected_requests: int = Field(..., description="Rejected requests")
    avg_approval_time_hours: float = Field(..., description="Average approval time in hours")


class CEODashboardData(BaseModel):
    """
    Complete CEO dashboard data.

    Aggregates all CEO-level metrics from all system layers.
    """

    timestamp: datetime = Field(..., description="Dashboard data timestamp")
    system: SystemOverview = Field(..., description="System overview")
    business: BusinessOverview = Field(..., description="Business operations overview")
    ai_team: AITeamOverview = Field(..., description="AI workforce overview")
    tasks: TaskOverview = Field(..., description="Task & workflow overview")
    approvals: ApprovalOverview = Field(..., description="Approval & governance overview")


__all__ = [
    "SystemOverview",
    "BusinessOverview",
    "AITeamOverview",
    "TaskOverview",
    "ApprovalOverview",
    "CEODashboardData",
]
