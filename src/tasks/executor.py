"""
Task Executor - Stage 5
Task execution engine
"""

from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.core.errors import ExecutionError
from src.core.events import EventBus
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User
from src.tasks.models import Task, TaskResult, TaskStatus
from src.tasks.service import TaskService

logger = structlog.get_logger(__name__)


class TaskExecutor:
    """
    Task Executor - Execute tasks

    Executes tasks by delegating to agents or systems.
    Manages execution lifecycle and error handling.
    """

    def __init__(
        self,
        task_service: TaskService,
        audit_service: Optional[AuditService] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.task_service = task_service
        self.audit_service = audit_service or AuditService()
        self.event_bus = event_bus or EventBus()
        logger.info("task_executor_initialized")

    async def execute_task(
        self,
        task_id: UUID,
        user: User,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute a task

        Args:
            task_id: Task ID
            user: User executing the task
            context: Execution context

        Returns:
            Task result

        Raises:
            ExecutionError: If execution fails
        """
        task = self.task_service.get_task(task_id, user)

        # Validate task state
        if task.status not in [TaskStatus.PENDING, TaskStatus.READY]:
            raise ExecutionError(f"Task cannot be executed in status: {task.status.value}")

        # Check dependencies
        completed_tasks = {
            t.id for t in self.task_service._tasks.values() if t.status == TaskStatus.COMPLETED
        }

        if not task.is_ready(completed_tasks):
            task.mark_blocked()
            raise ExecutionError("Task dependencies not satisfied")

        # Mark as running
        self.task_service.update_task_status(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            user=user,
        )

        # Audit start
        self.audit_service.log(
            action=AuditAction.UPDATE,
            resource_type="task_execution",
            resource_id=task.id,
            user_id=user.id,
            details={
                "task_type": task.task_type.value,
                "phase": "start",
            },
            status="success",
        )

        try:
            # Execute task
            result = await self._execute_task_logic(task, user, context)

            # Mark as completed
            self.task_service.update_task_status(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                user=user,
                result=result,
            )

            # Audit completion
            self.audit_service.log(
                action=AuditAction.UPDATE,
                resource_type="task_execution",
                resource_id=task.id,
                user_id=user.id,
                details={
                    "task_type": task.task_type.value,
                    "phase": "complete",
                    "success": result.success,
                },
                status="success",
            )

            logger.info(
                "task_executed_successfully",
                task_id=task.id,
                title=task.title,
                user_id=user.id,
            )

            return result

        except Exception as e:
            error_msg = str(e)

            # Check if can retry
            if task.can_retry():
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                logger.warning(
                    "task_execution_failed_will_retry",
                    task_id=task.id,
                    error=error_msg,
                    retry_count=task.retry_count,
                )
            else:
                # Mark as failed
                result = TaskResult(success=False, error=error_msg)
                self.task_service.update_task_status(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    user=user,
                    result=result,
                )

                logger.error(
                    "task_execution_failed",
                    task_id=task.id,
                    error=error_msg,
                )

            # Audit failure
            self.audit_service.log(
                action=AuditAction.UPDATE,
                resource_type="task_execution",
                resource_id=task.id,
                user_id=user.id,
                details={
                    "task_type": task.task_type.value,
                    "phase": "failed",
                    "error": error_msg,
                    "retry_count": task.retry_count,
                },
                status="failure",
            )

            raise ExecutionError(f"Task execution failed: {error_msg}") from e

    async def _execute_task_logic(
        self,
        task: Task,
        user: User,
        context: Optional[Dict[str, Any]],
    ) -> TaskResult:
        """
        Execute task logic

        This is a placeholder that should delegate to:
        - Agent Runtime (for AI tasks)
        - External systems (for integration tasks)
        - Custom executors (for specific task types)

        Args:
            task: Task to execute
            user: User executing task
            context: Execution context

        Returns:
            Task result
        """
        # Placeholder implementation
        # In real implementation, this would:
        # 1. Determine executor based on task type
        # 2. Delegate to appropriate agent/system
        # 3. Collect and return results

        logger.info(
            "task_execution_placeholder",
            task_id=task.id,
            task_type=task.task_type.value,
            message="Real execution would delegate to agents/systems",
        )

        # Simulate execution based on task type
        output = {
            "task_id": str(task.id),
            "task_type": task.task_type.value,
            "input_data": task.input_data,
            "executed_by": "placeholder_executor",
            "note": "This is a placeholder. Real execution would use Agent Runtime.",
        }

        return TaskResult(
            success=True,
            output=output,
            metadata={
                "executor_type": "placeholder",
                "task_type": task.task_type.value,
            },
        )

    async def execute_ready_tasks(
        self,
        user: User,
        max_concurrent: int = 5,
    ) -> list[TaskResult]:
        """
        Execute all ready tasks

        Args:
            user: User executing tasks
            max_concurrent: Max concurrent executions

        Returns:
            List of task results
        """
        ready_tasks = self.task_service.get_ready_tasks(user)

        if not ready_tasks:
            logger.info("no_ready_tasks")
            return []

        logger.info(
            "executing_ready_tasks",
            count=len(ready_tasks),
            max_concurrent=max_concurrent,
        )

        results = []
        for task in ready_tasks[:max_concurrent]:
            try:
                result = await self.execute_task(task.id, user)
                results.append(result)
            except ExecutionError as e:
                logger.warning(
                    "task_execution_skipped",
                    task_id=task.id,
                    error=str(e),
                )

        return results

    async def cancel_task(
        self,
        task_id: UUID,
        user: User,
    ) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task ID
            user: User cancelling task

        Returns:
            True if cancelled
        """
        task = self.task_service.get_task(task_id, user)

        if task.status not in [TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING]:
            raise ExecutionError(f"Task cannot be cancelled in status: {task.status.value}")

        # Mark as cancelled
        self.task_service.update_task_status(
            task_id=task.id,
            status=TaskStatus.CANCELLED,
            user=user,
        )

        # Audit
        self.audit_service.log(
            action=AuditAction.UPDATE,
            resource_type="task",
            resource_id=task.id,
            user_id=user.id,
            details={"action": "cancelled"},
            status="success",
        )

        logger.info("task_cancelled", task_id=task.id, user_id=user.id)

        return True
