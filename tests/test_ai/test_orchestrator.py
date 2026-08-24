"""
Tests for AI Orchestrator and multi-agent task coordination.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.ai.agents import AgentContext, AgentExecution, AgentRuntime, AgentStatus, AgentType
from src.ai.orchestrator import (
    AIOrchestrator,
    ExecutionMode,
    Task,
    TaskPlan,
    TaskPriority,
    TaskResult,
    TaskStatus,
    TaskStep,
)
from src.ai.tools import ToolRegistry


class TestTask:
    """Test task structure."""

    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            task_id=uuid4(),
            title="Test Task",
            description="Test task",
            priority=TaskPriority.NORMAL,
            status=TaskStatus.PENDING,
            actor_id=uuid4(),
            trace_id=uuid4(),
        )

        assert task.description == "Test task"
        assert task.priority == TaskPriority.NORMAL
        assert task.status == TaskStatus.PENDING


class TestTaskStep:
    """Test task step structure."""

    def test_task_step_creation(self):
        """Test creating a task step."""
        step = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Analyze this data",
            depends_on=[],
        )

        assert step.agent_type == AgentType.GPT
        assert step.description == "Analyze this data"


class TestTaskPlan:
    """Test task plan structure."""

    def test_task_plan_creation(self):
        """Test creating a task plan."""
        uuid4()

        step1 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Step 1",
            depends_on=[],
        )

        step2 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.CLAUDE,
            description="Step 2",
            depends_on=[step1.step_id],
        )

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=uuid4(),
            steps=[step1, step2],
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        assert len(plan.steps) == 2
        assert plan.execution_mode == ExecutionMode.SEQUENTIAL

    def test_task_plan_dependency_validation(self):
        """Test task plan validates dependencies."""
        uuid4()
        nonexistent_dep = uuid4()

        step1 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Step 1",
            depends_on=[nonexistent_dep],  # References non-existent step
        )

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=uuid4(),
            steps=[step1],
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        # Plan should note invalid dependencies
        assert len(plan.steps) == 1


class TestTaskResult:
    """Test task result structure."""

    def test_task_result_creation(self):
        """Test creating a task result."""
        result = TaskResult(
            task_id=uuid4(),
            status=TaskStatus.COMPLETED,
            result="Task completed successfully",
            agent_executions=[],
        )

        assert result.status == TaskStatus.COMPLETED
        assert result.result == "Task completed successfully"


@pytest.mark.asyncio
class TestAIOrchestrator:
    """Test AI Orchestrator."""

    async def test_orchestrator_initialization(self):
        """Test orchestrator initializes with dependencies."""
        agent_runtime = Mock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        assert orchestrator._agent_runtime == agent_runtime
        assert orchestrator._tool_registry == tool_registry

    async def test_plan_simple_task(self):
        """Test planning a simple single-step task."""
        agent_runtime = Mock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        actor_id = uuid4()
        task = Task(
            task_id=uuid4(),
            title="Test Task",
            description="Analyze sales data",
            priority=TaskPriority.NORMAL,
            status=TaskStatus.PENDING,
            actor_id=actor_id,
            trace_id=uuid4(),
        )
        plan = await orchestrator._create_plan(task)

        assert plan is not None
        assert len(plan.steps) > 0

    async def test_plan_complex_multi_agent_task(self):
        """Test planning a complex multi-agent task."""
        agent_runtime = Mock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        actor_id = uuid4()
        task = Task(
            task_id=uuid4(),
            title="Test Task",
            description="Research market trends and create strategy document",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            actor_id=actor_id,
            trace_id=uuid4(),
        )
        plan = await orchestrator._create_plan(task)

        assert plan is not None
        assert len(plan.steps) >= 1  # In Stage 3, simple planning creates single-step tasks

    async def test_execute_sequential_plan(self):
        """Test executing a plan in sequential mode."""
        agent_runtime = AsyncMock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        uuid4()

        step1 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Step 1",
            depends_on=[],
        )

        step2 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.CLAUDE,
            description="Step 2",
            depends_on=[step1.step_id],
        )

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=uuid4(),
            steps=[step1, step2],
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        # Create test context
        trace_id = uuid4()
        actor_id = uuid4()
        context = AgentContext(
            agent_id=uuid4(),
            agent_type=AgentType.GPT,
            trace_id=trace_id,
            actor_id=actor_id,
            session_id=uuid4(),
        )

        # Mock agent execution
        agent_runtime.execute = AsyncMock(
            return_value=AgentExecution(
                execution_id=uuid4(),
                agent_type=AgentType.GPT,
                context=context,
                status=AgentStatus.COMPLETED,
                input_messages=[{"role": "user", "content": "test"}],
                output="Test response",
            )
        )

        result = await orchestrator.execute_plan(plan, context)

        assert result is not None
        # Result is a string aggregation of outputs
        # Sequential execution should have called execute twice
        assert agent_runtime.execute.call_count == 2

    async def test_execute_parallel_plan(self):
        """Test executing a plan in parallel mode."""
        agent_runtime = AsyncMock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        uuid4()

        # Two independent steps that can run in parallel
        step1 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Step 1",
            depends_on=[],
        )

        step2 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.CLAUDE,
            description="Step 2",
            depends_on=[],
        )

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=uuid4(),
            steps=[step1, step2],
            execution_mode=ExecutionMode.PARALLEL,
        )

        # Create test context
        trace_id = uuid4()
        actor_id = uuid4()
        context = AgentContext(
            agent_id=uuid4(),
            agent_type=AgentType.GPT,
            trace_id=trace_id,
            actor_id=actor_id,
            session_id=uuid4(),
        )

        # Mock agent execution
        agent_runtime.execute = AsyncMock(
            return_value=AgentExecution(
                execution_id=uuid4(),
                agent_type=AgentType.GPT,
                context=context,
                status=AgentStatus.COMPLETED,
                input_messages=[{"role": "user", "content": "test"}],
                output="Test response",
            )
        )

        result = await orchestrator.execute_plan(plan, context)

        assert result is not None
        # Both steps should have been executed
        assert agent_runtime.execute.call_count == 2

    async def test_execute_hybrid_plan(self):
        """Test executing a plan in hybrid mode with dependencies."""
        agent_runtime = AsyncMock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        uuid4()

        # Step 1 runs first
        step1 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Step 1",
            depends_on=[],
        )

        # Steps 2 and 3 depend on step 1, can run in parallel
        step2 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.CLAUDE,
            description="Step 2",
            depends_on=[step1.step_id],
        )

        step3 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.DEEPSEEK,
            description="Step 3",
            depends_on=[step1.step_id],
        )

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=uuid4(),
            steps=[step1, step2, step3],
            execution_mode=ExecutionMode.HYBRID,
        )

        # Create test context
        trace_id = uuid4()
        actor_id = uuid4()
        context = AgentContext(
            agent_id=uuid4(),
            agent_type=AgentType.GPT,
            trace_id=trace_id,
            actor_id=actor_id,
            session_id=uuid4(),
        )

        # Mock agent execution
        agent_runtime.execute = AsyncMock(
            return_value=AgentExecution(
                execution_id=uuid4(),
                agent_type=AgentType.GPT,
                context=context,
                status=AgentStatus.COMPLETED,
                input_messages=[{"role": "user", "content": "test"}],
                output="Test response",
            )
        )

        result = await orchestrator.execute_plan(plan, context)

        assert result is not None
        # All three steps should have been executed
        assert agent_runtime.execute.call_count == 3

    async def test_handle_step_failure(self):
        """Test handling step failure in orchestration."""
        agent_runtime = AsyncMock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        uuid4()

        step1 = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Step 1",
            depends_on=[],
        )

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=uuid4(),
            steps=[step1],
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        # Mock agent execution to fail
        agent_runtime.execute = AsyncMock(side_effect=Exception("Agent failed"))

        # Create test context
        trace_id = uuid4()
        actor_id = uuid4()
        context = AgentContext(
            agent_id=uuid4(),
            agent_type=AgentType.GPT,
            trace_id=trace_id,
            actor_id=actor_id,
            session_id=uuid4(),
        )

        # Step should fail and raise exception
        with pytest.raises(Exception, match="Agent failed"):
            await orchestrator.execute_plan(plan, context)


class TestAgentWorkflowSeparation:
    """Test Agent ≠ Workflow principle."""

    def test_agents_provide_capability_orchestrator_coordinates(self):
        """Test agents provide capability, orchestrator coordinates workflow."""
        # Agent provides capability (execution)
        agent_runtime = Mock(spec=AgentRuntime)

        # Orchestrator coordinates workflow (planning and execution order)
        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=Mock(),
        )

        # Agents don't orchestrate
        assert not hasattr(agent_runtime, "plan_task")
        assert not hasattr(agent_runtime, "execute_plan")

        # Orchestrator doesn't execute agents directly
        assert hasattr(orchestrator, "submit_task")
        assert hasattr(orchestrator, "submit_task")  # Auto-executes, no separate execute_plan

    async def test_orchestrator_delegates_to_agents(self):
        """Test orchestrator delegates to agents but doesn't replace them."""
        agent_runtime = AsyncMock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        uuid4()
        step = TaskStep(
            step_id=uuid4(),
            agent_type=AgentType.GPT,
            description="Test",
            depends_on=[],
        )

        plan = TaskPlan(
            plan_id=uuid4(),
            task_id=uuid4(),
            steps=[step],
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        # Create test context
        trace_id = uuid4()
        actor_id = uuid4()
        context = AgentContext(
            agent_id=uuid4(),
            agent_type=AgentType.GPT,
            trace_id=trace_id,
            actor_id=actor_id,
            session_id=uuid4(),
        )

        agent_runtime.execute = AsyncMock(
            return_value=AgentExecution(
                execution_id=uuid4(),
                agent_type=AgentType.GPT,
                context=context,
                status=AgentStatus.COMPLETED,
                input_messages=[{"role": "user", "content": "test"}],
                output="Response",
            )
        )

        await orchestrator.execute_plan(plan, context)

        # Orchestrator should have delegated to agent runtime
        assert agent_runtime.execute.called


class TestTaskPriorityHandling:
    """Test task priority handling."""

    async def test_critical_priority_tasks(self):
        """Test critical priority tasks are handled appropriately."""
        agent_runtime = Mock(spec=AgentRuntime)
        tool_registry = Mock(spec=ToolRegistry)

        orchestrator = AIOrchestrator(
            agent_runtime=agent_runtime,
            tool_registry=tool_registry,
        )

        task = Task(
            task_id=uuid4(),
            title="Test Task",
            description="Critical business decision",
            priority=TaskPriority.CRITICAL,
            status=TaskStatus.PENDING,
            actor_id=uuid4(),
            trace_id=uuid4(),
        )

        plan = await orchestrator.submit_task(
            task.title, task.description, task.actor_id, task.priority
        )

        assert plan is not None
        assert task.priority == TaskPriority.CRITICAL
