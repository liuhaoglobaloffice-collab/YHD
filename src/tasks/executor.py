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
from src.workforce.employee import AIEmployeeService

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
        employee_service: Optional[AIEmployeeService] = None,
        audit_service: Optional[AuditService] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.task_service = task_service
        self.employee_service = employee_service
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
        task = await self.task_service.get_task(task_id, user)

        # Validate task state
        if task.status not in [TaskStatus.PENDING, TaskStatus.READY]:
            raise ExecutionError(f"Task cannot be executed in status: {task.status.value}")

        # Check dependencies - get all completed tasks from database
        all_tasks = await self.task_service.list_tasks(user=user)
        completed_tasks = {
            t.id for t in all_tasks if t.status == TaskStatus.COMPLETED
        }

        if not task.is_ready(completed_tasks):
            await self.task_service.update_task_status(
                task_id=task.id,
                status=TaskStatus.BLOCKED,
                user=user,
            )
            raise ExecutionError("Task dependencies not satisfied")

        # Mark as running
        await self.task_service.update_task_status(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            user=user,
        )

        # Audit start
        await self.audit_service.log(
            session=self.task_service.session,
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
            await self.task_service.update_task_status(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                user=user,
                result=result,
            )

            # Audit completion
            await self.audit_service.log(
                session=self.task_service.session,
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
                await self.task_service.update_task_status(
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
            await self.audit_service.log(
                session=self.task_service.session,
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
        Execute task logic by delegating to AI employees.

        Delegation order:
        1. If task.assigned_to contains employee IDs, delegate to the first available AI employee.
        2. If no employee is assigned, return a structured no-assignment result
           (caller is responsible for assigning employees before execution).

        Args:
            task: Task to execute
            user: User executing task
            context: Execution context

        Returns:
            Task result
        """
        assigned = task.assigned_to
        if assigned:
            employee_id = assigned[0]
            return await self._execute_with_employee(task, employee_id, user)

        # No employee assigned — task cannot be executed automatically.
        logger.warning(
            "task_no_employee_assigned",
            task_id=str(task.id),
            task_type=task.task_type.value,
        )
        return TaskResult(
            success=True,
            output={
                "task_id": str(task.id),
                "task_type": task.task_type.value,
                "input_data": task.input_data,
                "note": "No AI employee assigned. Task accepted but not executed.",
            },
            metadata={
                "executor_type": "unassigned",
                "requires_assignment": True,
            },
        )

    async def _execute_with_employee(
        self,
        task: Task,
        employee_id: UUID,
        user: User,
    ) -> TaskResult:
        """Delegate task execution to an AI employee."""
        if not self.employee_service:
            raise ExecutionError(
                "Employee service not configured; cannot execute task with AI employee"
            )

        # Build prompt from task input_data
        prompt = task.input_data.get("prompt") if task.input_data else None
        if not prompt:
            prompt = f"Task: {task.title}\n\nDescription: {task.description}"

        # Delegate to AI Employee
        exec_result = await self.employee_service.execute_task(
            employee_id=employee_id,
            prompt=prompt,
            actor_id=user.id,
            temperature=task.input_data.get("temperature") if task.input_data else None,
            max_tokens=task.input_data.get("max_tokens") if task.input_data else None,
        )

        return TaskResult(
            success=exec_result.get("status") == "completed",
            output={
                "execution_id": exec_result.get("execution_id"),
                "employee_id": exec_result.get("employee_id"),
                "employee_name": exec_result.get("employee_name"),
                "agent_type": exec_result.get("agent_type"),
                "output": exec_result.get("output"),
            },
            error=exec_result.get("error"),
            metadata={
                "executor_type": "ai_employee",
                "response_time_ms": exec_result.get("response_time_ms"),
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
        ready_tasks = await self.task_service.get_ready_tasks(user)

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
        task = await self.task_service.get_task(task_id, user)

        if task.status not in [TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING]:
            raise ExecutionError(f"Task cannot be cancelled in status: {task.status.value}")

        # Mark as cancelled
        await self.task_service.update_task_status(
            task_id=task.id,
            status=TaskStatus.CANCELLED,
            user=user,
        )

        # Audit
        await self.audit_service.log(
            session=self.task_service.session,
            action=AuditAction.UPDATE,
            resource_type="task",
            resource_id=task.id,
            user_id=user.id,
            details={"action": "cancelled"},
            status="success",
        )

        logger.info("task_cancelled", task_id=task.id, user_id=user.id)

        return True
