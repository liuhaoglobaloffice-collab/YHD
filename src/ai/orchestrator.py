"""
AI Orchestrator - Coordinates multi-agent task execution.

Enforces: Agent ≠ Workflow
Orchestrator coordinates agents, but agents themselves don't orchestrate.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..core.errors import ValidationError
from .agents import AgentContext, AgentExecution, AgentRuntime, AgentType
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(str, Enum):
    """Task execution modes."""

    SEQUENTIAL = "sequential"  # Execute agents one after another
    PARALLEL = "parallel"  # Execute agents concurrently
    HYBRID = "hybrid"  # Mix of sequential and parallel


@dataclass
class TaskStep:
    """Individual step in task plan."""

    step_id: UUID
    agent_type: AgentType
    description: str
    depends_on: List[UUID] = field(default_factory=list)  # Step IDs this step depends on
    input_messages: List[Dict[str, Any]] = field(default_factory=list)
    execution: Optional[AgentExecution] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class TaskPlan:
    """Execution plan for a task."""

    plan_id: UUID
    task_id: UUID
    steps: List[TaskStep]
    execution_mode: ExecutionMode
    estimated_duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Task:
    """High-level task for AI system."""

    task_id: UUID
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    actor_id: Optional[UUID]
    trace_id: UUID
    plan: Optional[TaskPlan] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Task execution result."""

    task_id: UUID
    status: TaskStatus
    result: Optional[str] = None
    agent_executions: List[AgentExecution] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIOrchestrator:
    """
    AI Orchestrator - Coordinates multi-agent task execution.

    Responsibilities:
    - Task planning and decomposition
    - Agent selection and coordination
    - Execution flow management (sequential, parallel, hybrid)
    - Result aggregation
    - Error handling and recovery

    Enforces:
    - Agent ≠ Workflow: Agents execute, orchestrator coordinates
    - Single Source of Truth: Only orchestrator coordinates agents
    """

    def __init__(self, agent_runtime: AgentRuntime, tool_registry: ToolRegistry):
        self._agent_runtime = agent_runtime
        self._tool_registry = tool_registry
        self._active_tasks: Dict[UUID, Task] = {}
        logger.info("AI Orchestrator initialized")

    async def submit_task(
        self,
        title: str,
        description: str,
        actor_id: Optional[UUID] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Submit a new task for execution.

        Returns task immediately, execution happens asynchronously.
        """
        task = Task(
            task_id=uuid4(),
            title=title,
            description=description,
            priority=priority,
            status=TaskStatus.PENDING,
            actor_id=actor_id,
            trace_id=uuid4(),
            metadata=metadata or {},
        )

        self._active_tasks[task.task_id] = task

        logger.info(f"Task submitted: {task.task_id} - {title}")

        # Start execution asynchronously
        asyncio.create_task(self._execute_task(task))

        return task

    async def _execute_task(self, task: Task):
        """Execute task through full lifecycle."""
        try:
            task.status = TaskStatus.PLANNING
            task.started_at = datetime.now(UTC)

            # Create execution plan
            plan = await self._create_plan(task)
            task.plan = plan

            task.status = TaskStatus.EXECUTING

            # Execute plan
            if plan.execution_mode == ExecutionMode.SEQUENTIAL:
                result = await self._execute_sequential(task, plan)
            elif plan.execution_mode == ExecutionMode.PARALLEL:
                result = await self._execute_parallel(task, plan)
            else:  # HYBRID
                result = await self._execute_hybrid(task, plan)

            # Update task
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now(UTC)

            logger.info(f"Task completed: {task.task_id}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(UTC)

            logger.error(f"Task failed: {task.task_id}: {e}")

    async def _create_plan(self, task: Task) -> TaskPlan:
        """
        Create execution plan for task.

        For Stage 3, we use simple heuristics:
        - Complex tasks → Multiple agents (GPT for planning, specialists for execution)
        - Research tasks → Gemini or Kimi
        - Technical tasks → Claude
        - Analysis tasks → DeepSeek
        - Intelligence tasks → Grok
        """
        steps = []

        # Simple heuristic: Use GPT (CEO Brain) for all tasks in Stage 3
        # More sophisticated planning will come in later stages
        step = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description=f"Execute task: {task.title}",
            input_messages=[{"role": "user", "content": task.description}],
        )
        steps.append(step)

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=task.task_id,
            steps=steps,
            execution_mode=ExecutionMode.SEQUENTIAL,
            estimated_duration_seconds=None,
        )

        logger.info(f"Created plan for task {task.task_id}: {len(steps)} steps")

        return plan

    async def _execute_sequential(self, task: Task, plan: TaskPlan) -> str:
        """Execute plan steps sequentially."""
        results = []

        for step in plan.steps:
            # Check dependencies
            for dep_id in step.depends_on:
                dep_step = next((s for s in plan.steps if s.step_id == dep_id), None)
                if (
                    not dep_step
                    or not dep_step.execution
                    or dep_step.execution.status.value != "completed"
                ):
                    raise ValidationError(
                        f"Step dependency not satisfied: {dep_id}",
                        details={"field": "depends_on", "value": str(dep_id)},
                    )

            # Create agent context
            context = AgentContext(
                agent_id=uuid4(),
                agent_type=step.agent_type,
                trace_id=task.trace_id,
                actor_id=task.actor_id,
                parent_task_id=task.task_id,
            )

            # Execute step
            step.started_at = datetime.now(UTC)
            execution = await self._agent_runtime.execute(
                agent_type=step.agent_type, messages=step.input_messages, context=context
            )
            step.execution = execution
            step.completed_at = datetime.now(UTC)

            if execution.output:
                results.append(execution.output)

        return "\n\n".join(results)

    async def _execute_parallel(self, task: Task, plan: TaskPlan) -> str:
        """Execute plan steps in parallel."""
        # Group steps by dependency level
        levels: List[List[TaskStep]] = []
        remaining = plan.steps.copy()

        while remaining:
            # Find steps with no unfulfilled dependencies
            level = []
            for step in remaining:
                # Check if all dependencies are not in remaining (have been scheduled)
                if step.depends_on:
                    deps_satisfied = all(
                        not any(s.step_id == dep_id and s in remaining for s in plan.steps)
                        for dep_id in step.depends_on
                    )
                else:
                    deps_satisfied = True

                if deps_satisfied:
                    level.append(step)

            if not level:
                raise ValidationError(
                    "Circular dependency detected in task plan",
                    details={"field": "depends_on", "value": "circular"},
                )

            levels.append(level)
            for step in level:
                remaining.remove(step)

        # Execute each level in parallel
        results = []
        for level in levels:
            level_results = await asyncio.gather(
                *[self._execute_step(step, task) for step in level]
            )
            results.extend([r for r in level_results if r])

        return "\n\n".join(results)

    async def _execute_hybrid(self, task: Task, plan: TaskPlan) -> str:
        """Execute plan with mixed sequential/parallel execution."""
        # For Stage 3, hybrid is same as parallel
        # More sophisticated hybrid execution will come in later stages
        return await self._execute_parallel(task, plan)

    async def _execute_step(self, step: TaskStep, task: Task) -> Optional[str]:
        """Execute a single step."""
        context = AgentContext(
            agent_id=uuid4(),
            agent_type=step.agent_type,
            trace_id=task.trace_id,
            actor_id=task.actor_id,
            parent_task_id=task.task_id,
        )

        step.started_at = datetime.now(UTC)
        execution = await self._agent_runtime.execute(
            agent_type=step.agent_type, messages=step.input_messages, context=context
        )
        step.execution = execution
        step.completed_at = datetime.now(UTC)

        return execution.output

    def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID."""
        return self._active_tasks.get(task_id)

    def list_tasks(
        self, status: Optional[TaskStatus] = None, actor_id: Optional[UUID] = None
    ) -> List[Task]:
        """List tasks with optional filters."""
        tasks = list(self._active_tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if actor_id:
            tasks = [t for t in tasks if t.actor_id == actor_id]

        return tasks

    async def execute_plan(self, plan: TaskPlan, context: AgentContext) -> Optional[str]:
        """Execute a task plan (test wrapper)."""
        # Create a temporary task for the plan
        task = Task(
            task_id=plan.task_id,
            title="Test Task",
            description="Executing test plan",
            priority=TaskPriority.NORMAL,
            status=TaskStatus.EXECUTING,
            actor_id=context.actor_id,
            trace_id=context.trace_id,
            plan=plan,
        )

        # Execute according to mode
        if plan.execution_mode == ExecutionMode.SEQUENTIAL:
            return await self._execute_sequential(task, plan)
        elif plan.execution_mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(task, plan)
        elif plan.execution_mode == ExecutionMode.HYBRID:
            return await self._execute_hybrid(task, plan)
        else:
            raise ValidationError(f"Unknown execution mode: {plan.execution_mode}")

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a running task."""
        task = self._active_tasks.get(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now(UTC)

        logger.info(f"Task cancelled: {task_id}")

        return True

    async def get_task_result(self, task_id: UUID) -> Optional[TaskResult]:
        """Get task execution result."""
        task = self._active_tasks.get(task_id)
        if not task:
            return None

        agent_executions = []
        if task.plan:
            for step in task.plan.steps:
                if step.execution:
                    agent_executions.append(step.execution)

        duration = None
        if task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()

        return TaskResult(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            agent_executions=agent_executions,
            error=task.error,
            duration_seconds=duration,
            metadata=task.metadata,
        )


class AIBrain:
    """
    AI Brain - CEO Command Processing System (Phase 3.1)

    Integrates all AI Brain components to process CEO natural language commands
    and convert them into executable workflows.

    Architecture:
        CEO Command → CommandProcessor → Planner → AgentRouter → WorkflowBridge → Workflow Engine

    Enforces:
        - Security First: RBAC permission checks
        - Audit Everything: All commands logged
        - Single Source of Truth: Only AIBrain creates AI workflows
    """

    def __init__(
        self,
        session: "AsyncSession",
        rbac_service: Optional["RBACService"] = None,
        audit_service: Optional["AuditService"] = None,
    ):
        from ..core.di import get_dependency
        from ..identity.audit import AuditService
        from ..identity.rbac import RBACService
        from .agent_router import AgentRouter
        from .command_processor import CEOCommandProcessor
        from .planner import IntelligentPlanner
        from .workflow_bridge import WorkflowBridge

        self.session = session
        self.rbac = rbac_service or get_dependency(RBACService)
        self.audit = audit_service or get_dependency(AuditService)

        # Initialize AI Brain components
        self.command_processor = CEOCommandProcessor()
        self.planner = IntelligentPlanner()
        self.agent_router = AgentRouter(session)
        self.workflow_bridge = WorkflowBridge(session)

        logger.info("AI Brain initialized")

    async def process_command(
        self,
        command_text: str,
        user: "User",
        priority: Optional["CommandPriority"] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> "CEOCommand":
        """
        Process CEO natural language command.

        Args:
            command_text: Natural language command (中文 or English)
            user: User issuing the command
            priority: Optional priority override
            context: Optional context (user preferences, history, etc.)

        Returns:
            CEOCommand with execution status

        Raises:
            PermissionError: If user lacks AI_BRAIN_COMMAND_EXECUTE permission

        Flow:
            1. Check RBAC permission
            2. Parse command
            3. Create task plan
            4. Route to agents
            5. Create workflow
            6. Submit for execution
            7. Audit log
        """
        from ..identity.audit import AuditAction
        from ..identity.rbac import Permission
        from .models import CEOCommand, CommandPriority, CommandStatus

        # Check permission
        if not await self.rbac.check_permission_by_id(user.id, Permission.AI_BRAIN_COMMAND_EXECUTE):
            await self.audit.log(
                session=self.session,
                user_id=user.id,
                action=AuditAction.PERMISSION_DENIED,
                resource_type="ai_brain_command",
                status="denied",
                details={"command": command_text},
            )
            raise PermissionError("User lacks AI_BRAIN_COMMAND_EXECUTE permission")

        # Create command record
        command = CEOCommand(
            command_id=uuid4(),
            command_text=command_text,
            user_id=user.id,
            goal="",  # Will be populated by parser
            priority=priority or CommandPriority.NORMAL,
            status=CommandStatus.PENDING,
        )

        try:
            # Step 1: Parse command
            command.status = CommandStatus.PLANNING
            parsed = self.command_processor.parse(command_text, context)
            command.goal = parsed.goal

            if priority is None:
                command.priority = parsed.priority

            logger.info(
                f'Parsed CEO command: goal="{parsed.goal}", '
                f"agents={parsed.required_agents}, priority={command.priority.value}"
            )

            # Step 2: Create task plan
            plan = self.planner.create_plan(parsed)

            # Step 3: Route tasks to agents
            assignments = await self.agent_router.route_tasks(plan)

            # Step 4: Create workflow
            workflow = await self.workflow_bridge.create_workflow_from_plan(
                plan=plan, assignments=assignments, user=user, command_id=command.command_id
            )

            command.task_plan_id = workflow.workflow_id
            command.workflow_id = workflow.workflow_id

            # Step 5: Submit workflow for execution
            command.status = CommandStatus.EXECUTING
            command.started_at = datetime.now(UTC)

            execution_id = await self.workflow_bridge.execute_workflow(workflow=workflow, user=user)

            # Success
            command.status = CommandStatus.COMPLETED
            command.completed_at = datetime.now(UTC)
            command.result = f"Workflow created and submitted: {execution_id}"

            # Audit log
            await self.audit.log(
                session=self.session,
                user_id=user.id,
                action=AuditAction.AI_BRAIN_COMMAND_CREATED,
                resource_type="ceo_command",
                resource_id=str(command.command_id),
                status="success",
                details={
                    "command": command_text,
                    "goal": command.goal,
                    "workflow_id": str(workflow.workflow_id),
                    "task_count": len(plan.tasks),
                },
            )

            logger.info(
                f"CEO command processed successfully: command_id={command.command_id}, "
                f"workflow_id={workflow.workflow_id}, tasks={len(plan.tasks)}"
            )

        except Exception as e:
            command.status = CommandStatus.FAILED
            command.error = str(e)
            command.completed_at = datetime.now(UTC)

            # Audit failure
            await self.audit.log(
                session=self.session,
                user_id=user.id,
                action=AuditAction.AI_BRAIN_COMMAND_CREATED,
                resource_type="ceo_command",
                resource_id=str(command.command_id),
                status="failed",
                details={
                    "command": command_text,
                    "error": str(e),
                },
            )

            logger.error(
                f"CEO command processing failed: command_id={command.command_id}, " f"error={e}"
            )

            raise

        return command

    async def get_command_status(self, command_id: UUID, user: "User") -> "CEOCommand":
        """
        Get status of CEO command execution.

        Args:
            command_id: Command ID
            user: User requesting status

        Returns:
            CEOCommand with current status

        Note:
            Phase 3.1: Returns in-memory command object.
            Future: Retrieve from database.
        """
        from ..identity.rbac import Permission

        # Check permission
        if not await self.rbac.check_permission_by_id(user.id, Permission.AI_BRAIN_PLAN_READ):
            raise PermissionError("User lacks AI_BRAIN_PLAN_READ permission")

        # Phase 3.1: Return placeholder
        # Future: Query from database
        logger.warning(f"get_command_status not fully implemented: {command_id}")

        from .models import CEOCommand, CommandPriority, CommandStatus

        return CEOCommand(
            command_id=command_id,
            command_text="",
            user_id=user.id,
            goal="Status query not implemented",
            priority=CommandPriority.NORMAL,
            status=CommandStatus.PENDING,
        )
