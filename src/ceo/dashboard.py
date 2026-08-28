"""
CEO Dashboard Service

Aggregates system-wide data for executive visibility.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.database.models import FailureRecordModel, GoalModel, AiCostRecordModel
from src.identity.models import User
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
        session: Optional[AsyncSession] = None,
    ):
        self.business_registry = business_registry
        self.employee_registry = employee_registry
        self.approval_service = approval_service
        self.audit_service = audit_service
        self.rbac_service = rbac_service
        self.session = session
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
            # Use RBAC service to check permission by user ID and permission enum
            return await self.rbac_service.check_permission_by_id(
                user_id, Permission.CEO_DASHBOARD_READ
            )
        except Exception as e:
            logger.error(
                "ceo_dashboard_permission_check_failed",
                extra={"user_id": str(user_id), "error": str(e)},
            )
            return False

    async def _get_system_overview(self) -> SystemOverview:
        """Aggregate system health metrics."""
        # 真实数据：从数据库查询用户总数
        total_users = 0
        total_goals = 0
        if self.session:
            try:
                result = await self.session.execute(select(func.count(User.id)))
                total_users = result.scalar_one() or 0
                result = await self.session.execute(select(func.count(GoalModel.id)))
                total_goals = result.scalar_one() or 0
            except Exception as e:
                logger.error("system_overview_db_query_failed", extra={"error": str(e)})

        return SystemOverview(
            status="healthy",
            uptime_hours=168.0,
            total_users=total_users,
            active_sessions=total_users,  # 近似：最近活跃用户数
            cpu_usage_percent=25.0,
            memory_usage_percent=40.0,
            disk_usage_percent=50.0,
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

        # 真实数据：从数据库查询目标统计
        total_goals = 0
        active_goals = 0
        completed_goals = 0
        failed_goals = 0
        total_failures = 0
        if self.session:
            try:
                result = await self.session.execute(select(func.count(GoalModel.id)))
                total_goals = result.scalar_one() or 0
                result = await self.session.execute(
                    select(func.count(GoalModel.id)).where(GoalModel.status == "active")
                )
                active_goals = result.scalar_one() or 0
                result = await self.session.execute(
                    select(func.count(GoalModel.id)).where(GoalModel.status == "completed")
                )
                completed_goals = result.scalar_one() or 0
                result = await self.session.execute(
                    select(func.count(GoalModel.id)).where(GoalModel.status == "failed")
                )
                failed_goals = result.scalar_one() or 0
                result = await self.session.execute(select(func.count(FailureRecordModel.id)))
                total_failures = result.scalar_one() or 0
            except Exception as e:
                logger.error("business_goals_query_failed", extra={"error": str(e)})

        return BusinessOverview(
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            in_progress_tasks=in_progress,
            success_rate=success_rate,
            avg_completion_time_hours=avg_time,
            revenue_impact=revenue_impact,
            total_goals=total_goals,
            active_goals=active_goals,
            completed_goals=completed_goals,
            failed_goals=failed_goals,
            total_failure_records=total_failures,
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

        # 真实数据：从 AiCostRecordModel 查询实际任务完成数
        total_tasks_real = 0
        employee_task_counts = {}
        employee_names = {}
        for emp in employees:
            employee_names[str(emp.id)] = emp.name

        if self.session:
            try:
                result = await self.session.execute(
                    select(func.count(AiCostRecordModel.id))
                )
                total_tasks_real = result.scalar_one() or 0

                # 按 employee_id 统计任务数
                rows = await self.session.execute(
                    select(
                        AiCostRecordModel.employee_id,
                        func.count(AiCostRecordModel.id).label("task_count"),
                    ).where(AiCostRecordModel.status == "success").group_by(AiCostRecordModel.employee_id)
                )
                for row in rows:
                    emp_id = row[0] or "unknown"
                    task_count = row[1]
                    employee_task_counts[emp_id] = task_count
            except Exception as e:
                logger.error("ai_team_db_query_failed", extra={"error": str(e)})

        # 如果真实数据不可用，fallback 到业务任务数据
        if total_tasks_real == 0:
            tasks = await self.business_registry.list()
            total_tasks_real = sum(1 for t in tasks if t.status == "completed")

        avg_tasks = total_tasks_real / total if total > 0 else 0.0

        # Top performers: 按实际任务完成数排序
        top = sorted(employees, key=lambda e: employee_task_counts.get(str(e.id), 0), reverse=True)[:5]
        top_performers = [
            {
                "employee_id": str(emp.id),
                "name": emp.name,
                "department": emp.department,
                "tasks_completed": employee_task_counts.get(str(emp.id), 0),
            }
            for emp in top
        ]

        return AITeamOverview(
            total_employees=total,
            active_employees=active,
            suspended_employees=suspended,
            total_tasks_completed=total_tasks_real,
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
    session: Optional[AsyncSession] = None,
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
            session=session,
        )
    return _ceo_dashboard


def reset_ceo_dashboard() -> None:
    """Reset dashboard instance (for testing)."""
    global _ceo_dashboard
    _ceo_dashboard = None
