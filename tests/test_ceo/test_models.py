"""
Test CEO Models
"""

from datetime import UTC, datetime

from src.ceo.models import (
    AITeamOverview,
    ApprovalOverview,
    BusinessOverview,
    CEODashboardData,
    SystemOverview,
    TaskOverview,
)


class TestSystemOverview:
    """Test SystemOverview model."""

    def test_create_system_overview(self):
        """Test creating SystemOverview."""
        overview = SystemOverview(
            status="healthy",
            uptime_hours=100.0,
            total_users=50,
            active_sessions=10,
            cpu_usage_percent=30.0,
            memory_usage_percent=45.0,
            disk_usage_percent=60.0,
        )

        assert overview.status == "healthy"
        assert overview.uptime_hours == 100.0
        assert overview.total_users == 50
        assert overview.active_sessions == 10

    def test_system_overview_serialization(self):
        """Test SystemOverview can serialize to dict."""
        overview = SystemOverview(
            status="degraded",
            uptime_hours=50.0,
            total_users=100,
            active_sessions=20,
            cpu_usage_percent=80.0,
            memory_usage_percent=70.0,
            disk_usage_percent=75.0,
        )

        data = overview.model_dump()
        assert data["status"] == "degraded"
        assert data["cpu_usage_percent"] == 80.0


class TestBusinessOverview:
    """Test BusinessOverview model."""

    def test_create_business_overview(self):
        """Test creating BusinessOverview."""
        overview = BusinessOverview(
            total_tasks=100,
            completed_tasks=80,
            failed_tasks=5,
            in_progress_tasks=15,
            success_rate=94.1,
            avg_completion_time_hours=2.5,
            revenue_impact=8000.0,
        )

        assert overview.total_tasks == 100
        assert overview.completed_tasks == 80
        assert overview.success_rate == 94.1

    def test_business_overview_zero_tasks(self):
        """Test BusinessOverview with zero tasks."""
        overview = BusinessOverview(
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            in_progress_tasks=0,
            success_rate=0.0,
            avg_completion_time_hours=0.0,
            revenue_impact=0.0,
        )

        assert overview.total_tasks == 0
        assert overview.success_rate == 0.0


class TestAITeamOverview:
    """Test AITeamOverview model."""

    def test_create_ai_team_overview(self):
        """Test creating AITeamOverview."""
        overview = AITeamOverview(
            total_employees=10,
            active_employees=8,
            suspended_employees=2,
            total_tasks_completed=500,
            avg_tasks_per_employee=50.0,
            top_performers=[
                {
                    "employee_id": "emp-1",
                    "name": "GPT Agent",
                    "department": "CEO Office",
                    "tasks_completed": 100,
                },
            ],
        )

        assert overview.total_employees == 10
        assert overview.active_employees == 8
        assert len(overview.top_performers) == 1

    def test_ai_team_overview_no_employees(self):
        """Test AITeamOverview with no employees."""
        overview = AITeamOverview(
            total_employees=0,
            active_employees=0,
            suspended_employees=0,
            total_tasks_completed=0,
            avg_tasks_per_employee=0.0,
            top_performers=[],
        )

        assert overview.total_employees == 0
        assert len(overview.top_performers) == 0


class TestTaskOverview:
    """Test TaskOverview model."""

    def test_create_task_overview(self):
        """Test creating TaskOverview."""
        overview = TaskOverview(
            total_tasks=200,
            pending_tasks=50,
            running_tasks=30,
            completed_tasks=100,
            failed_tasks=20,
        )

        assert overview.total_tasks == 200
        assert overview.pending_tasks == 50
        assert overview.completed_tasks == 100

    def test_task_overview_empty(self):
        """Test TaskOverview with no tasks."""
        overview = TaskOverview(
            total_tasks=0,
            pending_tasks=0,
            running_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
        )

        assert overview.total_tasks == 0


class TestApprovalOverview:
    """Test ApprovalOverview model."""

    def test_create_approval_overview(self):
        """Test creating ApprovalOverview."""
        overview = ApprovalOverview(
            total_requests=50,
            pending_requests=10,
            approved_requests=35,
            rejected_requests=5,
            avg_approval_time_hours=3.5,
        )

        assert overview.total_requests == 50
        assert overview.pending_requests == 10
        assert overview.approved_requests == 35

    def test_approval_overview_zero_requests(self):
        """Test ApprovalOverview with zero requests."""
        overview = ApprovalOverview(
            total_requests=0,
            pending_requests=0,
            approved_requests=0,
            rejected_requests=0,
            avg_approval_time_hours=0.0,
        )

        assert overview.total_requests == 0
        assert overview.avg_approval_time_hours == 0.0


class TestCEODashboardData:
    """Test CEODashboardData model."""

    def test_create_ceo_dashboard_data(self):
        """Test creating complete CEODashboardData."""
        timestamp = datetime.now(UTC)

        dashboard = CEODashboardData(
            timestamp=timestamp,
            system=SystemOverview(
                status="healthy",
                uptime_hours=100.0,
                total_users=50,
                active_sessions=10,
                cpu_usage_percent=30.0,
                memory_usage_percent=45.0,
                disk_usage_percent=60.0,
            ),
            business=BusinessOverview(
                total_tasks=100,
                completed_tasks=80,
                failed_tasks=5,
                in_progress_tasks=15,
                success_rate=94.1,
                avg_completion_time_hours=2.5,
                revenue_impact=8000.0,
            ),
            ai_team=AITeamOverview(
                total_employees=10,
                active_employees=8,
                suspended_employees=2,
                total_tasks_completed=500,
                avg_tasks_per_employee=50.0,
                top_performers=[],
            ),
            tasks=TaskOverview(
                total_tasks=200,
                pending_tasks=50,
                running_tasks=30,
                completed_tasks=100,
                failed_tasks=20,
            ),
            approvals=ApprovalOverview(
                total_requests=50,
                pending_requests=10,
                approved_requests=35,
                rejected_requests=5,
                avg_approval_time_hours=3.5,
            ),
        )

        assert dashboard.timestamp == timestamp
        assert dashboard.system.status == "healthy"
        assert dashboard.business.total_tasks == 100
        assert dashboard.ai_team.total_employees == 10
        assert dashboard.tasks.total_tasks == 200
        assert dashboard.approvals.total_requests == 50

    def test_ceo_dashboard_data_serialization(self):
        """Test CEODashboardData serialization."""
        dashboard = CEODashboardData(
            timestamp=datetime.now(UTC),
            system=SystemOverview(
                status="healthy",
                uptime_hours=100.0,
                total_users=50,
                active_sessions=10,
                cpu_usage_percent=30.0,
                memory_usage_percent=45.0,
                disk_usage_percent=60.0,
            ),
            business=BusinessOverview(
                total_tasks=100,
                completed_tasks=80,
                failed_tasks=5,
                in_progress_tasks=15,
                success_rate=94.1,
                avg_completion_time_hours=2.5,
                revenue_impact=8000.0,
            ),
            ai_team=AITeamOverview(
                total_employees=10,
                active_employees=8,
                suspended_employees=2,
                total_tasks_completed=500,
                avg_tasks_per_employee=50.0,
                top_performers=[],
            ),
            tasks=TaskOverview(
                total_tasks=200,
                pending_tasks=50,
                running_tasks=30,
                completed_tasks=100,
                failed_tasks=20,
            ),
            approvals=ApprovalOverview(
                total_requests=50,
                pending_requests=10,
                approved_requests=35,
                rejected_requests=5,
                avg_approval_time_hours=3.5,
            ),
        )

        data = dashboard.model_dump()
        assert "timestamp" in data
        assert data["system"]["status"] == "healthy"
        assert data["business"]["total_tasks"] == 100
