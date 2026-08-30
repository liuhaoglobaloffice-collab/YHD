"""
AI Employee Performance Tracker.

Tracks and analyzes AI employee performance metrics.
"""

import logging
from datetime import UTC, datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from .models import EmployeePerformanceRecord
from .registry import AIEmployeeRegistry

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Tracks AI Employee performance metrics.

    Metrics:
    - Task completion rate
    - Execution time
    - Success/failure ratio
    - Quality scores
    - User ratings
    """

    def __init__(self, registry: AIEmployeeRegistry):
        self.registry = registry
        self._records: Dict[UUID, List[EmployeePerformanceRecord]] = {}  # employee_id -> records
        logger.info("Performance Tracker initialized")

    async def record_performance(
        self,
        employee_id: UUID,
        task_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        success: bool = False,
        execution_time_seconds: float = 0.0,
        cost_usd: float = 0.0,
        user_rating: Optional[int] = None,
        quality_score: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> EmployeePerformanceRecord:
        """
        Record a performance event for an employee.

        Args:
            employee_id: Employee UUID
            task_id: Task UUID (optional)
            workflow_id: Workflow UUID (optional)
            success: Whether the task succeeded
            execution_time_seconds: Execution time in seconds
            cost_usd: Cost in USD
            user_rating: User rating (1-5 stars)
            quality_score: Quality score (0.0-1.0)
            error_message: Error message if failed
            metadata: Additional metadata

        Returns:
            Created performance record

        Raises:
            ResourceNotFoundError: If employee not found
        """
        # Verify employee exists
        employee = await self.registry.get(employee_id)

        # Create record
        record = EmployeePerformanceRecord(
            id=uuid4(),
            employee_id=employee_id,
            task_id=task_id,
            workflow_id=workflow_id,
            success=success,
            execution_time_seconds=execution_time_seconds,
            cost_usd=cost_usd,
            user_rating=user_rating,
            quality_score=quality_score,
            error_message=error_message,
            metadata=metadata or {},
        )

        # Store record (in-memory read cache)
        if employee_id not in self._records:
            self._records[employee_id] = []
        self._records[employee_id].append(record)

        # 落库（best-effort）：绩效是信任评分与自我学习的数据底座，
        # 只放内存会导致重启清零、信任分永远退化为默认值。
        session = getattr(self.registry, "session", None)
        if session is not None:
            try:
                from src.database.models import EmployeePerformanceModel

                history = self._records.get(employee_id, [])
                completed = sum(1 for r in history if r.success)
                failed = sum(1 for r in history if not r.success)
                total = completed + failed
                now = datetime.now(UTC)

                row = EmployeePerformanceModel(
                    id=str(record.id),
                    employee_id=str(employee_id),
                    tasks_completed=completed,
                    tasks_failed=failed,
                    avg_execution_time_seconds=(
                        sum(r.execution_time_seconds for r in history) / total if total else 0.0
                    ),
                    success_rate=(completed / total) if total else 0.0,
                    user_rating=float(user_rating) if user_rating else None,
                    period_start=now,
                    period_end=now,
                    meta={
                        "task_id": str(task_id) if task_id else None,
                        "workflow_id": str(workflow_id) if workflow_id else None,
                        "cost_usd": cost_usd,
                        "execution_time_seconds": execution_time_seconds,
                        "success": success,
                        "quality_score": quality_score,
                        "error_message": error_message,
                        "metadata": metadata or {},
                        "recorded_at": now.isoformat(),
                    },
                    created_at=now,
                )
                session.add(row)
                await session.commit()
            except Exception:
                logger.warning("performance_persist_failed", exc_info=True)

        # Update employee aggregate stats
        employee.total_execution_time_seconds += execution_time_seconds
        employee.total_cost_usd += cost_usd

        if success:
            employee.tasks_completed += 1
        else:
            employee.tasks_failed += 1

        employee.updated_at = datetime.now(UTC)
        await self.registry.update(employee_id, employee)

        logger.info(
            f"Recorded performance for {employee.name}: "
            f"success={success}, time={execution_time_seconds}s, cost=${cost_usd}",
            extra={"employee_id": str(employee_id), "task_id": str(task_id)},
        )

        return record

    async def get_employee_performance(
        self,
        employee_id: UUID,
    ) -> List[EmployeePerformanceRecord]:
        """
        Get all performance records for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            List of performance records
        """
        # Verify employee exists
        await self.registry.get(employee_id)

        return self._records.get(employee_id, [])

    async def get_performance_summary(
        self,
        employee_id: UUID,
    ) -> Dict:
        """
        Get performance summary for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            Performance summary dictionary
        """
        employee = await self.registry.get(employee_id)
        records = self._records.get(employee_id, [])

        total_tasks = employee.tasks_completed + employee.tasks_failed
        success_rate = employee.tasks_completed / total_tasks if total_tasks > 0 else 0.0

        # Calculate average metrics
        avg_execution_time = (
            employee.total_execution_time_seconds / total_tasks if total_tasks > 0 else 0.0
        )

        avg_cost = employee.total_cost_usd / total_tasks if total_tasks > 0 else 0.0

        # Calculate average rating
        ratings = [r.user_rating for r in records if r.user_rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        # Calculate average quality score
        quality_scores = [r.quality_score for r in records if r.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

        return {
            "employee_id": str(employee_id),
            "employee_name": employee.name,
            "total_tasks": total_tasks,
            "tasks_completed": employee.tasks_completed,
            "tasks_failed": employee.tasks_failed,
            "success_rate": success_rate,
            "total_execution_time_seconds": employee.total_execution_time_seconds,
            "average_execution_time_seconds": avg_execution_time,
            "total_cost_usd": employee.total_cost_usd,
            "average_cost_usd": avg_cost,
            "average_user_rating": avg_rating,
            "average_quality_score": avg_quality,
            "total_records": len(records),
        }

    async def get_top_performers(
        self,
        metric: str = "success_rate",
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get top performing employees by a metric.

        Args:
            metric: Metric to sort by (success_rate, tasks_completed, average_rating)
            limit: Maximum number of results

        Returns:
            List of employee summaries sorted by metric
        """
        summaries = []

        for employee_id in self.registry._employees.keys():
            try:
                summary = await self.get_performance_summary(employee_id)
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to get summary for {employee_id}: {e}")

        # Sort by metric
        if metric == "success_rate":
            summaries.sort(key=lambda s: s["success_rate"], reverse=True)
        elif metric == "tasks_completed":
            summaries.sort(key=lambda s: s["tasks_completed"], reverse=True)
        elif metric == "average_rating":
            summaries.sort(key=lambda s: s["average_user_rating"] or 0.0, reverse=True)

        return summaries[:limit]

    def clear_records(self, employee_id: UUID) -> None:
        """
        Clear all performance records for an employee.

        Args:
            employee_id: Employee UUID
        """
        if employee_id in self._records:
            del self._records[employee_id]
            logger.info(f"Cleared performance records for {employee_id}")
