"""
Task Executor - Stage 5
Task execution engine with RecoveryChain integration.
"""

from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.recovery import RecoveryChain, StrategyAction
from src.ai.recovery_executor import RecoveryExecutor
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
    Task Executor - Execute tasks with failure recovery.

    Execution flow:
    TaskExecutor.execute_task()
        │
        ├─ Success → mark COMPLETED → return TaskResult
        │
        └─ Failure → RecoveryChain.record_failure()
                        │
                        └─ RecoveryChain.determine_strategy()
                            │
                            ├─ RETRY → re-execute (up to max_retries)
                            │
                            └─ ABORT → mark FAILED
                                        │
                                        └─ record_lesson()
    """

    def __init__(
        self,
        task_service: TaskService,
        employee_service: Optional[AIEmployeeService] = None,
        audit_service: Optional[AuditService] = None,
        event_bus: Optional[EventBus] = None,
        session: Optional[AsyncSession] = None,
    ):
        self.task_service = task_service
        self.employee_service = employee_service
        self.audit_service = audit_service or AuditService()
        self.event_bus = event_bus or EventBus()
        self.session = session or task_service.session
        self.recovery_chain = RecoveryChain(self.session) if self.session else None
        self.recovery_executor = RecoveryExecutor(self.session) if self.session else None
        self._task_repo = None  # Lazy-loaded
        logger.info("task_executor_initialized")

    async def _persist_retry_count(self, task: Task) -> None:
        """Persist task retry_count to database between retries."""
        if not self.session:
            return
        from src.database.repositories.task import TaskRepository
        repo = TaskRepository(self.session)
        await repo.update(str(task.id), {"retry_count": task.retry_count})

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

        # ── Retry loop with RecoveryChain integration ──
        max_attempts = 1 + task.max_retries
        last_error = None
        recovery_record = None

        for attempt in range(1, max_attempts + 1):
            try:
                # Execute task logic
                result = await self._execute_task_logic(task, user, context)

                # Check result.success — AI employee failure is not a success
                if not result.success:
                    raise ExecutionError(result.error or "Task execution returned failure")

                # Mark as completed
                await self.task_service.update_task_status(
                    task_id=task.id,
                    status=TaskStatus.COMPLETED,
                    user=user,
                    result=result,
                )

                # Record lesson if recovery was involved
                if attempt > 1 and recovery_record and self.recovery_chain:
                    try:
                        await self.recovery_chain.record_lesson(
                            recovery_record.id,
                            f"Task recovered after {attempt - 1} retries",
                            True,
                        )
                    except Exception:
                        logger.warning("recovery_lesson_record_failed", exc_info=True)

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
                    attempt=attempt,
                )

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "task_execution_failed",
                    task_id=task.id,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=last_error,
                )

                # ── Record failure in RecoveryChain ──
                if attempt < max_attempts and self.recovery_chain:
                    try:
                        record = await self.recovery_chain.record_failure(
                            failure_summary=f"Task {task.title} execution failed",
                            failure_detail=last_error,
                            task_id=str(task.id),
                            workflow_id=str(task.workflow_id) if task.workflow_id else None,
                            created_by=user.id,
                        )
                        strategy = await self.recovery_chain.determine_strategy(record, context or {})
                        recovery_record = record

                        if strategy == StrategyAction.RETRY:
                            task.retry_count += 1
                            # Persist retry_count to database between retries
                            await self._persist_retry_count(task)
                            # RecoveryExecutor registers the retry
                            if self.recovery_executor:
                                await self.recovery_executor._execute_retry(record, {})
                            logger.info(
                                "task_recovery_retry",
                                task_id=task.id,
                                retry_count=task.retry_count,
                                max_retries=task.max_retries,
                            )
                            continue  # → Retry execution

                        elif strategy == StrategyAction.ABORT:
                            logger.warning(
                                "task_recovery_abort",
                                task_id=task.id,
                                strategy=strategy.value,
                            )
                            break  # Can't recover

                        elif strategy == StrategyAction.REQUEST_BOSS:
                            logger.warning(
                                "task_recovery_request_boss",
                                task_id=task.id,
                                strategy=strategy.value,
                            )
                            break  # Need boss decision

                        else:
                            # SWITCH_AGENT, SWITCH_PROVIDER, ADJUST_PARAMS, CHANGE_APPROACH
                            # These are retry-compatible strategies — continue the retry loop
                            logger.info(
                                "task_recovery_retry_with_strategy",
                                task_id=task.id,
                                strategy=strategy.value,
                            )
                            continue

                    except Exception as recovery_err:
                        logger.warning("recovery_chain_error", error=str(recovery_err))

                # No more retries or strategy is not RETRY
                break

        # ── Final failure — all retries exhausted ──
        error_msg = last_error or "Unknown error"
        result = TaskResult(success=False, error=error_msg)
        await self.task_service.update_task_status(
            task_id=task.id,
            status=TaskStatus.FAILED,
            user=user,
            result=result,
        )

        # Record final lesson
        if recovery_record and self.recovery_chain:
            try:
                await self.recovery_chain.record_lesson(
                    recovery_record.id,
                    f"Task failed after all retries: {error_msg}",
                    False,
                )
            except Exception:
                logger.warning("recovery_final_lesson_failed", exc_info=True)

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

        logger.error(
            "task_execution_failed_final",
            task_id=task.id,
            title=task.title,
            error=error_msg,
            retry_count=task.retry_count,
        )

        raise ExecutionError(f"Task execution failed: {error_msg}")

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
        # ⚠️ 不允许无员工时静默返回成功，必须真实失败
        logger.error(
            "task_no_employee_assigned",
            task_id=str(task.id),
            task_type=task.task_type.value,
        )
        return TaskResult(
            success=False,
            output={
                "task_id": str(task.id),
                "task_type": task.task_type.value,
                "note": "No AI employee assigned. Task cannot be executed without an assigned employee.",
            },
            error="No AI employee assigned to task. Ensure the task has an assigned employee before execution.",
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

        # ── 提取 workflow context 安全传递给 AIEmployeeService ──
        context_data = None
        if task.input_data and "_workflow_context" in task.input_data:
            raw_ctx = task.input_data["_workflow_context"]
            # 只提取安全上下文（不含内部控制字段）
            if isinstance(raw_ctx, dict):
                safe_ctx = {}
                step_results = raw_ctx.get("step_results", {})
                variables = raw_ctx.get("variables", {})
                if step_results:
                    safe_ctx["step_results"] = step_results
                if variables:
                    safe_ctx["variables"] = variables
                context_data = safe_ctx if safe_ctx else None

        # 注入调用链标识：使 AI 调用成本/绩效可按 task、workflow、goal 归集
        context_data = dict(context_data or {})
        context_data.setdefault("task_id", str(task.id))
        if task.workflow_id:
            context_data["workflow_id"] = str(task.workflow_id)
        if not context_data:
            context_data = None

        # Delegate to AI Employee
        exec_result = await self.employee_service.execute_task(
            employee_id=employee_id,
            prompt=prompt,
            actor_id=user.id,
            temperature=task.input_data.get("temperature") if task.input_data else None,
            max_tokens=task.input_data.get("max_tokens") if task.input_data else None,
            context_data=context_data,
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
