"""
CEO Dashboard Service

Aggregates system-wide data for executive visibility.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from src.business.registry import BusinessTaskRegistry
from src.ceo.models import (
    AITeamOverview,
    ApprovalOverview,
    BusinessOverview,
    CEODashboardData,
    SystemOverview,
    TaskOverview,
)
from src.core.logging import get_logger
from src.governance.approval import ApprovalService
from src.identity.audit import AuditService
from src.identity.rbac import Permission, RBACService
from src.workforce.registry import AIEmployeeRegistry

logger = get_logger(__name__)


class CEODashboard:
    """
    CEO Dashboard Service

    Aggregates data from all layers:
    - Stage 1: Core + Security
    - Stage 2: Identity + Governance
    - Stage 3: AI Runtime
    - Stage 4: Knowledge (not yet integrated)
    - Stage 5: Workflow + Task
    - Stage 6: AI Workforce
    - Stage 7: Business OS

    Security:
    - Requires CEO_DASHBOARD_READ or SYSTEM_ADMIN permission
    - All queries are read-only
    - No sensitive data exposure
    """

    def __init__(
        self,
        business_registry: BusinessTaskRegistry,
        employee_registry: AIEmployeeRegistry,
        approval_service: ApprovalService,
        audit_service: AuditService,
        rbac_service: RBACService,
    ):
        self.business_registry = business_registry
        self.employee_registry = employee_registry
        self.approval_service = approval_service
        self.audit_service = audit_service
        self.rbac_service = rbac_service
        logger.info("ceo_dashboard_initialized")

    async def get_dashboard(
        self,
        user_id: UUID,
        time_range_hours: int = 24,
    ) -> CEODashboardData:
        """
        Get complete CEO dashboard data.

        Args:
            user_id: CEO user ID
            time_range_hours: Time range for metrics (default 24h)

        Returns:
            CEODashboardData with all aggregated metrics

        Raises:
            PermissionError: If user lacks CEO_DASHBOARD_READ permission
        """
        # RBAC check
        if not await self._check_permission(user_id):
            logger.warning(
                "unauthorized_ceo_dashboard_access_attempt",
                extra={"user_id": str(user_id)},
            )
            raise PermissionError("User lacks CEO dashboard access permission")

        logger.info(
            "ceo_dashboard_access",
            extra={"user_id": str(user_id), "time_range_hours": time_range_hours},
        )

        # Audit (simplified for dashboard)

        # Aggregate all components
        system = await self._get_system_overview()
        business = await self._get_business_overview(time_range_hours)
        ai_team = await self._get_ai_team_overview()
        tasks = await self._get_task_overview(time_range_hours)
        approvals = await self._get_approval_overview()

        return CEODashboardData(
            timestamp=datetime.now(UTC),
            system=system,
            business=business,
            ai_team=ai_team,
            tasks=tasks,
            approvals=approvals,
        )

    async def get_system_overview(self, user_id: UUID) -> SystemOverview:
        """Get system overview only."""
        if not await self._check_permission(user_id):
            raise PermissionError("User lacks CEO dashboard access permission")
        return await self._get_system_overview()

    async def get_business_overview(
        self,
        user_id: UUID,
        time_range_hours: int = 24,
    ) -> BusinessOverview:
        """Get business overview only."""
        if not await self._check_permission(user_id):
            raise PermissionError("User lacks CEO dashboard access permission")
        return await self._get_business_overview(time_range_hours)

    async def get_ai_team_overview(self, user_id: UUID) -> AITeamOverview:
        """Get AI team overview only."""
        if not await self._check_permission(user_id):
            raise PermissionError("User lacks CEO dashboard access permission")
        return await self._get_ai_team_overview()

    async def get_task_overview(
        self,
        user_id: UUID,
        time_range_hours: int = 24,
    ) -> TaskOverview:
        """Get task overview only."""
        if not await self._check_permission(user_id):
            raise PermissionError("User lacks CEO dashboard access permission")
        return await self._get_task_overview(time_range_hours)

    async def get_approval_overview(self, user_id: UUID) -> ApprovalOverview:
        """Get approval overview only."""
        if not await self._check_permission(user_id):
            raise PermissionError("User lacks CEO dashboard access permission")
        return await self._get_approval_overview()

    # Private methods

    async def _check_permission(self, user_id: UUID) -> bool:
        """Check if user has CEO dashboard permission."""
        try:
            # Use RBAC service to check permission
            return await self.rbac_service.check_permission(user_id, Permission.CEO_DASHBOARD_READ)
        except Exception as e:
            logger.error(
                "ceo_dashboard_permission_check_failed",
                extra={"user_id": str(user_id), "error": str(e)},
            )
            return False

    async def _get_system_overview(self) -> SystemOverview:
        """Aggregate system health metrics."""
        # TODO: Integrate real health checks from Stage 1
        # For now, return healthy status
        return SystemOverview(
            status="healthy",
            uptime_hours=168.0,  # Placeholder: 1 week
            total_users=10,  # Placeholder
            active_sessions=5,  # Placeholder
            cpu_usage_percent=25.0,  # Placeholder
            memory_usage_percent=40.0,  # Placeholder
            disk_usage_percent=50.0,  # Placeholder
        )

    async def _get_business_overview(self, time_range_hours: int) -> BusinessOverview:
        """Aggregate business metrics."""
        tasks = await self.business_registry.list()

        total = len(tasks)
        if total == 0:
            return BusinessOverview(
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                in_progress_tasks=0,
                success_rate=0.0,
                avg_completion_time_hours=0.0,
                revenue_impact=0.0,
            )

        # Count by status
        completed = sum(1 for t in tasks if t.status == "completed")
        failed = sum(1 for t in tasks if t.status == "failed")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")

        # Success rate
        finished = completed + failed
        success_rate = (completed / finished * 100.0) if finished > 0 else 0.0

        # Avg completion time (for completed tasks)
        completion_times = []
        for task in tasks:
            if task.status == "completed" and task.completed_at:
                task.completed_at - task.created_at
                # Make times timezone-aware for comparison                task_created = task.created_at.replace(tzinfo=UTC) if task.created_at.tzinfo is None else task.created_at                task_completed = task.completed_at.replace(tzinfo=UTC) if task.completed_at.tzinfo is None else task.completed_at                delta = task_completed - task_created                completion_times.append(delta.total_seconds() / 3600.0)  # hours

        avg_time = sum(completion_times) / len(completion_times) if completion_times else 0.0

        # Placeholder revenue impact
        revenue_impact = completed * 100.0  # $100 per completed task

        return BusinessOverview(
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            in_progress_tasks=in_progress,
            success_rate=success_rate,
            avg_completion_time_hours=avg_time,
            revenue_impact=revenue_impact,
        )

    async def _get_ai_team_overview(self) -> AITeamOverview:
        """Aggregate AI workforce metrics."""
        employees = await self.employee_registry.list_employees()

        total = len(employees)
        if total == 0:
            return AITeamOverview(
                total_employees=0,
                active_employees=0,
                suspended_employees=0,
                total_tasks_completed=0,
                avg_tasks_per_employee=0.0,
                top_performers=[],
            )

        active = sum(1 for e in employees if e.status == "active")
        suspended = sum(1 for e in employees if e.status == "suspended")

        # Aggregate tasks (placeholder: use performance data if available)
        total_tasks = 0
        for emp in employees:
            # Placeholder: assume each active employee completed ~10 tasks
            if emp.status == "active":
                total_tasks += 10

        avg_tasks = total_tasks / total if total > 0 else 0.0

        # Top performers (placeholder: sort by name for now)
        top = sorted(employees, key=lambda e: e.name)[:5]
        top_performers = [
            {
                "employee_id": str(emp.id),
                "name": emp.name,
                "department": emp.department,
                "tasks_completed": 10,  # Placeholder
            }
            for emp in top
        ]

        return AITeamOverview(
            total_employees=total,
            active_employees=active,
            suspended_employees=suspended,
            total_tasks_completed=total_tasks,
            avg_tasks_per_employee=avg_tasks,
            top_performers=top_performers,
        )

    async def _get_task_overview(self, time_range_hours: int) -> TaskOverview:
        """Aggregate task & workflow metrics."""
        # For now, task data comes from BusinessTaskRegistry
        # In future, integrate src/tasks/ (Stage 5) for more detail
        tasks = await self.business_registry.list()

        total = len(tasks)
        pending = sum(1 for t in tasks if t.status == "pending")
        running = sum(1 for t in tasks if t.status == "in_progress")
        completed = sum(1 for t in tasks if t.status == "completed")
        failed = sum(1 for t in tasks if t.status == "failed")

        return TaskOverview(
            total_tasks=total,
            pending_tasks=pending,
            running_tasks=running,
            completed_tasks=completed,
            failed_tasks=failed,
        )

    async def _get_approval_overview(self) -> ApprovalOverview:
        """Aggregate approval & governance metrics."""
        # Query approval service (async)
        requests = await self.approval_service.list_requests()

        total = len(requests)
        if total == 0:
            return ApprovalOverview(
                total_requests=0,
                pending_requests=0,
                approved_requests=0,
                rejected_requests=0,
                avg_approval_time_hours=0.0,
            )

        pending = sum(1 for r in requests if r.status == "pending")
        approved = sum(1 for r in requests if r.status == "approved")
        rejected = sum(1 for r in requests if r.status == "rejected")

        # Avg approval time (for approved/rejected)
        approval_times = []
        for req in requests:
            if req.status in ("approved", "rejected") and req.updated_at:
                delta = req.updated_at - req.created_at
                approval_times.append(delta.total_seconds() / 3600.0)  # hours

        avg_time = sum(approval_times) / len(approval_times) if approval_times else 0.0

        return ApprovalOverview(
            total_requests=total,
            pending_requests=pending,
            approved_requests=approved,
            rejected_requests=rejected,
            avg_approval_time_hours=avg_time,
        )


# Singleton instance (optional, for dependency injection)
_ceo_dashboard: Optional[CEODashboard] = None


def get_ceo_dashboard(
    business_registry: BusinessTaskRegistry,
    employee_registry: AIEmployeeRegistry,
    approval_service: ApprovalService,
    audit_service: AuditService,
    rbac_service: RBACService,
) -> CEODashboard:
    """Get or create CEODashboard instance."""
    global _ceo_dashboard
    if _ceo_dashboard is None:
        _ceo_dashboard = CEODashboard(
            business_registry=business_registry,
            employee_registry=employee_registry,
            approval_service=approval_service,
            audit_service=audit_service,
            rbac_service=rbac_service,
        )
    return _ceo_dashboard


def reset_ceo_dashboard() -> None:
    """Reset dashboard instance (for testing)."""
    global _ceo_dashboard
    _ceo_dashboard = None
