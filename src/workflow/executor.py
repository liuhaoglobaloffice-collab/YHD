"""
Workflow Executor - Stage 5
Execute workflow definitions with different patterns (sequential, parallel, conditional, loop)

⚠️ 当前实现为同步顺序执行，缺少异步 Task Queue / Worker Pool。
   长时间运行的工作流会阻塞当前请求，建议后续引入 Celery / Redis Queue。
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.recovery import RecoveryChain, StrategyAction
from src.ai.recovery_executor import RecoveryExecutor
from src.core.di import get_dependency
from src.core.events import Event, EventBus
from src.database.repositories.converters import workflow_execution_to_model
from src.database.repositories.workflow import WorkflowExecutionRepository
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User
from src.identity.rbac import Permission, RBACService
from src.tasks.executor import TaskExecutor
from src.tasks.models import TaskPriority, TaskType
from src.tasks.service import TaskService
from src.workflow.models import (
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStep,
    WorkflowStepType,
)
from src.workflow.service import WorkflowService

logger = structlog.get_logger(__name__)

# 单个步骤执行超时（秒），防止长时间任务阻塞
STEP_TIMEOUT_SECONDS = 300  # 5 分钟

# 工作流上下文序列化安全限制（字符数）
MAX_CONTEXT_CHARS = 10000


class WorkflowExecutor:
    """
    Workflow Executor - Execute workflows with different patterns

    Execution Patterns:
    1. SEQUENTIAL - Execute steps one after another
    2. PARALLEL - Execute steps concurrently using asyncio.gather
    3. CONDITIONAL - Branch based on condition evaluation
    4. LOOP - Repeat steps based on loop criteria
    5. TASK - Execute single task via TaskService

    Security:
    - All executions require RBAC permission checks
    - All operations are audited
    - Fail Closed: Unknown patterns/errors default to failure
    """

    def __init__(
        self,
        workflow_service: Optional[WorkflowService] = None,
        task_service: Optional[TaskService] = None,
        task_executor: Optional[TaskExecutor] = None,
        rbac_service: Optional[RBACService] = None,
        audit_service: Optional[AuditService] = None,
        event_bus: Optional[EventBus] = None,
        session: Optional[AsyncSession] = None,
    ):
        self.workflow_service = workflow_service or get_dependency(WorkflowService)
        self.task_service = task_service or get_dependency(TaskService)
        self.task_executor = task_executor
        self.rbac = rbac_service or get_dependency(RBACService)
        self.audit = audit_service or get_dependency(AuditService)
        self.event_bus = event_bus or get_dependency(EventBus)
        self.session = session
        self._execution_repo = WorkflowExecutionRepository(session) if session else None

        # 失败恢复链（仅在注入 session 时可用）
        self._recovery = RecoveryChain(session) if session else None
        self._recovery_executor = RecoveryExecutor(session) if session else None

        # In-memory execution storage
        self._executions: Dict[UUID, WorkflowExecution] = {}

        # 重试追踪
        self._retry_counts: Dict[str, int] = {}

        logger.info("workflow_executor_initialized")

    async def _persist_execution(self, execution: WorkflowExecution) -> None:
        """Persist WorkflowExecution state to database."""
        if not self._execution_repo:
            return

        exists = await self._execution_repo.exists(str(execution.execution_id))
        if exists:
            await self._execution_repo.update(
                str(execution.execution_id),
                {
                    "status": execution.status.value,
                    "variables": execution.variables,
                    "result": execution.result,
                    "error": execution.error,
                    "meta": execution.metadata,
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                },
            )
        else:
            model = workflow_execution_to_model(execution)
            await self._execution_repo.create(model)

        await self.session.commit()

    async def execute_workflow(
        self,
        workflow_id: UUID,
        user: User,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow

        Args:
            workflow_id: Workflow to execute
            user: User executing the workflow
            variables: Initial workflow variables
            metadata: Execution metadata

        Returns:
            Workflow execution record

        Raises:
            PermissionError: If user lacks permission
            ValueError: If workflow not found or invalid
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_EXECUTE):
            await self.audit.log(
                session=self.session,
                action=AuditAction.WORKFLOW_EXECUTE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="denied",
                details={"reason": "permission_denied"},
            )
            raise PermissionError("User lacks WORKFLOW_EXECUTE permission")

        # Get workflow
        workflow = await self.workflow_service.get_workflow(workflow_id, user)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Create execution
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            started_by=user.id,
            variables=variables or {},
            metadata=metadata or {},
        )

        self._executions[execution.execution_id] = execution

        # Persist PENDING status
        await self._persist_execution(execution)

        # Audit
        await self.audit.log(
            session=self.session,
            action=AuditAction.WORKFLOW_EXECUTE,
            user_id=user.id,
            resource_type="workflow",
            resource_id=str(workflow_id),
            status="started",
            details={
                "execution_id": str(execution.execution_id),
                "variables": variables or {},
            },
        )

        # Emit event
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    name="workflow.execution.started",
                    data={
                        "workflow_id": str(workflow_id),
                        "execution_id": str(execution.execution_id),
                        "user_id": user.id,
                    },
                )
            )

        # Execute workflow steps
        try:
            execution.status = WorkflowExecutionStatus.RUNNING
            execution.started_at = datetime.now(UTC)

            # Persist RUNNING status
            await self._persist_execution(execution)

            results = []
            for step in workflow.steps:
                step_result = await self._execute_step(step, execution, user)
                results.append(step_result)

            execution.status = WorkflowExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.result = {"results": results}

            # Persist COMPLETED status
            await self._persist_execution(execution)

            # Audit success
            await self.audit.log(
                session=self.session,
                action=AuditAction.WORKFLOW_EXECUTE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="completed",
                details={
                    "execution_id": str(execution.execution_id),
                    "duration_seconds": (
                        execution.completed_at - execution.started_at
                    ).total_seconds(),
                },
            )

            # Emit event
            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        name="workflow.execution.completed",
                        data={
                            "workflow_id": str(workflow_id),
                            "execution_id": str(execution.execution_id),
                            "user_id": user.id,
                        },
                    )
                )

        except Exception as e:
            error_msg = str(e)
            execution.status = WorkflowExecutionStatus.FAILED
            execution.completed_at = datetime.now(UTC)
            execution.error = error_msg

            # Persist initial FAILED status
            await self._persist_execution(execution)

            # Step 1: 记录失败到恢复链
            recovery_strategy = None
            if self._recovery:
                try:
                    record = await self._recovery.record_failure(
                        failure_summary=f"Workflow {workflow_id} execution failed",
                        failure_detail=error_msg,
                        workflow_id=str(workflow_id),
                        created_by=user.id,
                        tenant_id=getattr(user, "tenant_id", None),
                    )
                    # 确定恢复策略
                    strategy = await self._recovery.determine_strategy(record)
                    recovery_strategy = strategy.value
                    execution.metadata["recovery_record_id"] = record.id
                    execution.metadata["recovery_strategy"] = strategy.value

                    # Step 2: 通过 RecoveryExecutor 自动执行恢复策略
                    if self._recovery_executor:
                        strategy_result = await self._recovery_executor.execute_strategy(
                            record, context={"workflow_id": str(workflow_id), "error": error_msg}
                        )
                        execution.metadata["recovery_result"] = {
                            "success": strategy_result.success,
                            "action": strategy_result.action,
                            "message": strategy_result.message,
                        }

                        # Step 3: 如果策略是 RETRY 且未超过阈值，重新执行工作流
                        if strategy == StrategyAction.RETRY and strategy_result.success:
                            retry_count = record.retry_count
                            max_retries = self._recovery.SAFETY_THRESHOLDS["max_retries"]
                            logger.info(
                                "workflow_recovery_retry",
                                workflow_id=str(workflow_id),
                                attempt=retry_count,
                                max_retries=max_retries,
                            )
                            # 重置执行状态，重新执行
                            execution.status = WorkflowExecutionStatus.RUNNING
                            execution.error = None
                            execution.completed_at = None

                            # Persist retry RUNNING status
                            await self._persist_execution(execution)
                            try:
                                results = []
                                for step in workflow.steps:
                                    step_result = await self._execute_step(step, execution, user)
                                    results.append(step_result)
                                execution.status = WorkflowExecutionStatus.COMPLETED
                                execution.completed_at = datetime.now(UTC)
                                execution.result = {
                                    "results": results,
                                    "recovered": True,
                                    "retry_attempt": retry_count,
                                }
                                # Persist retry COMPLETED status
                                await self._persist_execution(execution)
                                # 记录成功恢复经验
                                await self._recovery.record_lesson(
                                    record.id,
                                    f"RecoveryExecutor retry succeeded on attempt {retry_count}",
                                    True,
                                )
                            except Exception as retry_e:
                                execution.status = WorkflowExecutionStatus.FAILED
                                execution.completed_at = datetime.now(UTC)
                                execution.error = str(retry_e)
                                # Persist retry FAILED status
                                await self._persist_execution(execution)
                                await self._recovery.record_lesson(
                                    record.id,
                                    f"RecoveryExecutor retry failed: {retry_e}",
                                    False,
                                )

                except Exception as recovery_e:
                    logger.error("recovery_chain_error", error=str(recovery_e))

            # Audit failure
            await self.audit.log(
                session=self.session,
                action=AuditAction.WORKFLOW_EXECUTE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="failed" if execution.status == WorkflowExecutionStatus.FAILED else "completed",
                details={
                    "execution_id": str(execution.execution_id),
                    "error": error_msg,
                    "recovery_strategy": recovery_strategy,
                },
            )

            # Emit event
            if self.event_bus:
                event_name = "workflow.execution.recovered" if execution.status == WorkflowExecutionStatus.COMPLETED else "workflow.execution.failed"
                self.event_bus.publish(
                    Event(
                        name=event_name,
                        data={
                            "workflow_id": str(workflow_id),
                            "execution_id": str(execution.execution_id),
                            "user_id": user.id,
                            "error": execution.error,
                            "recovery_strategy": recovery_strategy,
                        },
                    )
                )

            if execution.status == WorkflowExecutionStatus.FAILED:
                logger.error(
                    "workflow_execution_failed",
                    workflow_id=str(workflow_id),
                    execution_id=str(execution.execution_id),
                    error=error_msg,
                    recovery_strategy=recovery_strategy,
                )

        return execution

    async def pause_execution(self, execution_id: UUID, user: User) -> None:
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_EXECUTE):
            raise PermissionError("User lacks WORKFLOW_EXECUTE permission")

        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if execution.status != WorkflowExecutionStatus.RUNNING:
            raise ValueError(f"Execution {execution_id} is not running")

        execution.status = WorkflowExecutionStatus.PAUSED

        # Persist PAUSED status
        await self._persist_execution(execution)

        await self.audit.log(
            session=self.session,
            action=AuditAction.WORKFLOW_EXECUTE,
            user_id=user.id,
            resource_type="workflow_execution",
            resource_id=str(execution_id),
            status="paused",
            details={"workflow_id": str(execution.workflow_id)},
        )

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    name="workflow.execution.paused",
                    data={
                        "execution_id": str(execution_id),
                        "workflow_id": str(execution.workflow_id),
                        "user_id": user.id,
                    },
                )
            )

    async def resume_execution(self, execution_id: UUID, user: User) -> None:
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_EXECUTE):
            raise PermissionError("User lacks WORKFLOW_EXECUTE permission")

        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if execution.status != WorkflowExecutionStatus.PAUSED:
            raise ValueError(f"Execution {execution_id} is not paused")

        execution.status = WorkflowExecutionStatus.RUNNING

        # Persist RUNNING status
        await self._persist_execution(execution)

        await self.audit.log(
            session=self.session,
            action=AuditAction.WORKFLOW_EXECUTE,
            user_id=user.id,
            resource_type="workflow_execution",
            resource_id=str(execution_id),
            status="resumed",
            details={"workflow_id": str(execution.workflow_id)},
        )

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    name="workflow.execution.resumed",
                    data={
                        "execution_id": str(execution_id),
                        "workflow_id": str(execution.workflow_id),
                        "user_id": user.id,
                    },
                )
            )

    async def cancel_execution(self, execution_id: UUID, user: User) -> None:
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_EXECUTE):
            raise PermissionError("User lacks WORKFLOW_EXECUTE permission")

        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        if execution.status in [
            WorkflowExecutionStatus.COMPLETED,
            WorkflowExecutionStatus.FAILED,
            WorkflowExecutionStatus.CANCELLED,
        ]:
            raise ValueError(f"Execution {execution_id} already finished")

        execution.status = WorkflowExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(UTC)

        # Persist CANCELLED status
        await self._persist_execution(execution)

        await self.audit.log(
            session=self.session,
            action=AuditAction.WORKFLOW_EXECUTE,
            user_id=user.id,
            resource_type="workflow_execution",
            resource_id=str(execution_id),
            status="cancelled",
            details={"workflow_id": str(execution.workflow_id)},
        )

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    name="workflow.execution.cancelled",
                    data={
                        "execution_id": str(execution_id),
                        "workflow_id": str(execution.workflow_id),
                        "user_id": user.id,
                    },
                )
            )

    async def get_execution(self, execution_id: UUID, user: User) -> Optional[WorkflowExecution]:
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_READ):
            raise PermissionError("User lacks WORKFLOW_READ permission")

        return self._executions.get(execution_id)

    async def list_executions(
        self,
        workflow_id: UUID,
        user: User,
        status: Optional[WorkflowExecutionStatus] = None,
    ) -> List[WorkflowExecution]:
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_READ):
            raise PermissionError("User lacks WORKFLOW_READ permission")

        executions = [e for e in self._executions.values() if e.workflow_id == workflow_id]

        if status:
            executions = [e for e in executions if e.status == status]

        return executions

    # ========== Private Execution Methods ==========

    async def _execute_step(
        self, step: WorkflowStep, execution: WorkflowExecution, user: User
    ) -> Any:
        step_type = WorkflowStepType(step.step_type)

        logger.info(
            "executing_step",
            step_id=step.step_id,
            step_type=step.step_type,
            execution_id=str(execution.execution_id),
        )

        # 带超时的步骤执行
        try:
            if step_type == WorkflowStepType.TASK:
                return await asyncio.wait_for(
                    self._execute_task_step(step, execution, user),
                    timeout=STEP_TIMEOUT_SECONDS,
                )
            elif step_type == WorkflowStepType.SEQUENTIAL:
                return await asyncio.wait_for(
                    self._execute_sequential_step(step, execution, user),
                    timeout=STEP_TIMEOUT_SECONDS,
                )
            elif step_type == WorkflowStepType.PARALLEL:
                return await asyncio.wait_for(
                    self._execute_parallel_step(step, execution, user),
                    timeout=STEP_TIMEOUT_SECONDS,
                )
            elif step_type == WorkflowStepType.CONDITIONAL:
                return await asyncio.wait_for(
                    self._execute_conditional_step(step, execution, user),
                    timeout=STEP_TIMEOUT_SECONDS,
                )
            elif step_type == WorkflowStepType.LOOP:
                return await asyncio.wait_for(
                    self._execute_loop_step(step, execution, user),
                    timeout=STEP_TIMEOUT_SECONDS,
                )
            else:
                raise ValueError(f"Unknown step type: {step.step_type}")
        except asyncio.TimeoutError:
            error_msg = f"Step '{step.name}' timed out after {STEP_TIMEOUT_SECONDS}s"
            logger.error("step_timeout", step_id=step.step_id, error=error_msg)
            raise TimeoutError(error_msg)

    async def _execute_task_step(
        self, step: WorkflowStep, execution: WorkflowExecution, user: User
    ) -> Any:
        config = step.task_config or {}

        # ── 注入 workflow context 到 task input_data ──
        input_data = dict(config.get("input_data", {}))
        if execution.variables is not None:
            # 安全上下文：只暴露非内部控制字段
            safe_context = {
                k: v for k, v in execution.variables.items() if not k.startswith("_")
            }
            input_data["_workflow_context"] = {
                "step_results": dict(execution.step_results),
                "variables": safe_context,
            }
            # 如果存在前序步骤结果且当前没有显式 prompt，自动构建含上下文的 prompt
            if not input_data.get("prompt") and execution.step_results:
                context_summary = self._build_step_context(execution.step_results)
                if context_summary:
                    input_data["prompt"] = (
                        f"前序步骤已完成，结果如下：\n\n{context_summary}\n\n"
                        f"请基于以上上下文完成当前任务：{step.name}"
                    )

        # Create task via TaskService (with workflow context injected)
        # Parse assigned_to from config if present (for workflow-level employee assignment)
        task_assigned_to = None
        raw_assigned = config.get("assigned_to")
        if raw_assigned:
            task_assigned_to = [UUID(a) if isinstance(a, str) else a for a in raw_assigned]
        # Also check for employee_id from WorkflowBridge step config
        raw_employee_id = config.get("employee_id")
        if raw_employee_id and not task_assigned_to:
            task_assigned_to = [UUID(raw_employee_id) if isinstance(raw_employee_id, str) else raw_employee_id]

        task = await self.task_service.create_task(
            title=step.name,
            description=config.get("description", ""),
            task_type=TaskType(config.get("task_type", "general")),
            user=user,
            priority=TaskPriority(config.get("priority", "medium")),
            assigned_to=task_assigned_to,
            workflow_id=execution.workflow_id,
            input_data=input_data,
            metadata={
                "execution_id": str(execution.execution_id),
                "step_id": step.step_id,
            },
        )

        logger.info(
            "task_step_created",
            step_id=step.step_id,
            task_id=str(task.id),
            execution_id=str(execution.execution_id),
        )

        # Execute the task via TaskExecutor if available
        if self.task_executor:
            try:
                result = await self.task_executor.execute_task(task.id, user, context=input_data)
                logger.info(
                    "task_step_executed",
                    step_id=step.step_id,
                    task_id=str(task.id),
                    execution_id=str(execution.execution_id),
                    success=result.success,
                )
                # If the task executor returned a failure, propagate to fail the workflow
                if not result.success:
                    error_msg = result.error or "Task execution returned failure"
                    # 写入失败结果，不留伪造的 completed
                    step_result = {
                        "task_id": str(task.id),
                        "status": "failed",
                        "result": result.output,
                        "error": error_msg,
                    }
                    execution.mark_step_failed(step.step_id, error_msg)
                    execution.variables[f"_step_{step.step_id}"] = {"error": error_msg}
                    await self._persist_execution(execution)
                    raise RuntimeError(error_msg)

                # ── 成功：写入 step_results 和 variables ──
                step_result = {
                    "task_id": str(task.id),
                    "status": result.metadata.get("task_status", "completed"),
                    "result": result.output,
                    "error": result.error,
                }
                execution.record_step_result(step.step_id, step_result)
                # 将步骤输出写入 variables 供后续步骤读取
                execution.variables[f"_step_{step.step_id}"] = result.output
                # 持久化中间状态
                await self._persist_execution(execution)
                return step_result
            except Exception as e:
                error_msg = str(e)
                logger.error(
                    "task_step_execution_failed",
                    step_id=step.step_id,
                    task_id=str(task.id),
                    execution_id=str(execution.execution_id),
                    error=error_msg,
                )
                # Re-raise so the workflow execution catches this and sets FAILED status
                raise

        return {"task_id": str(task.id), "status": task.status.value}

    async def _execute_sequential_step(
        self, step: WorkflowStep, execution: WorkflowExecution, user: User
    ) -> List[Any]:
        if not step.steps:
            return []

        results = []
        for substep in step.steps:
            result = await self._execute_step(substep, execution, user)
            results.append(result)

        return results

    async def _execute_parallel_step(
        self, step: WorkflowStep, execution: WorkflowExecution, user: User
    ) -> List[Any]:
        if not step.steps:
            return []

        # Execute all substeps concurrently
        tasks = [self._execute_step(substep, execution, user) for substep in step.steps]
        results = await asyncio.gather(*tasks)

        return list(results)

    async def _execute_conditional_step(
        self, step: WorkflowStep, execution: WorkflowExecution, user: User
    ) -> Any:
        config = step.task_config or {}
        condition = config.get("condition", "")

        # Evaluate condition
        if self._evaluate_condition(condition, execution.variables):
            # Execute 'then' branch
            if step.steps and len(step.steps) > 0:
                return await self._execute_step(step.steps[0], execution, user)
        else:
            # Execute 'else' branch
            if step.steps and len(step.steps) > 1:
                return await self._execute_step(step.steps[1], execution, user)

        return None

    async def _execute_loop_step(
        self, step: WorkflowStep, execution: WorkflowExecution, user: User
    ) -> int:
        if not step.steps:
            return 0

        config = step.task_config or {}
        max_iterations = config.get("max_iterations", 10)
        condition = config.get("condition", "")

        iterations = 0
        while iterations < max_iterations:
            # Check loop condition
            if condition and not self._evaluate_condition(condition, execution.variables):
                break

            # Execute loop body
            for substep in step.steps:
                await self._execute_step(substep, execution, user)

            iterations += 1

        return iterations

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        # Simple stub: check if condition is in variables and truthy
        if not condition:
            return True

        # Basic variable check: "var_name" or "var_name == value"
        if "==" in condition:
            parts = condition.split("==")
            if len(parts) == 2:
                var_name = parts[0].strip()
                expected = parts[1].strip().strip('"').strip("'")
                return str(variables.get(var_name)) == expected
        else:
            return bool(variables.get(condition.strip()))

        # Fail Closed: Unknown condition format defaults to False
        return False

    def _build_step_context(self, step_results: Dict[str, Any]) -> str:
        """Build a human-readable summary of previous step results for context injection.

        Args:
            step_results: Dict mapping step_id to step result dicts

        Returns:
            Truncated string summary of previous step outputs
        """
        parts = []
        total_len = 0
        for step_id, result in step_results.items():
            if isinstance(result, dict):
                output = result.get("result") or result.get("output", "")
                status = result.get("status", "completed")
                name = result.get("name", step_id)
            else:
                output = str(result) if result else ""
                status = "completed"
                name = step_id

            if isinstance(output, dict):
                try:
                    output = json.dumps(output, ensure_ascii=False, default=str)
                except (TypeError, ValueError):
                    output = str(output)

            entry = f"[{name}] (status: {status}):\n{output}"
            if total_len + len(entry) > MAX_CONTEXT_CHARS:
                remaining = MAX_CONTEXT_CHARS - total_len
                if remaining > 100:
                    parts.append(entry[:remaining] + "...[截断]")
                break
            parts.append(entry)
            total_len += len(entry)

        return "\n\n".join(parts)
