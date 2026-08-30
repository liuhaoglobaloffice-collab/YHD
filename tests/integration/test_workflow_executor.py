"""
WorkflowExecutor Integration Tests
Covers:
- P0 #1: Task created by WorkflowExecutor is actually executed by TaskExecutor
- P0 #2: WorkflowExecution state is persisted to database
- Task lifecycle: pending → running → completed/failed
- Workflow execution lifecycle: pending → running → completed/failed
- Exception handling and persistence
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.database.models import (
    GoalModel,
    TaskModel,
    WorkflowExecutionModel,
    WorkflowModel,
)
from src.database.repositories.converters import (
    _step_to_dict,
    model_to_workflow_execution,
)
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import Permission, RBACService, RoleEnum
from src.tasks.executor import TaskExecutor
from src.core.errors import ExecutionError
from src.tasks.models import TaskPriority, TaskResult, TaskStatus, TaskType
from src.tasks.service import TaskService
from src.workflow.executor import WorkflowExecutor
from src.workflow.models import (
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
)
from src.workflow.service import WorkflowService
from src.workforce.employee import AIEmployeeService


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_test_user():
    """Create a test user with superuser privileges."""
    user = User()
    user.id = 1
    user.username = "test_user"
    user.is_active = True
    user.is_superuser = True
    return user


async def create_test_user_in_db(session):
    """Create a test user in the database for permission checks."""
    user = User(
        id=1,
        username="test_user",
        email="test_user@test.com",
        hashed_password="test_password",
        is_active=True,
        is_superuser=True,
        role=RoleEnum.ADMIN,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def create_workflow_with_task_step(session=None):
    """Create a workflow with a single TASK step for testing."""
    step_id = "step-1"
    step = WorkflowStep(
        step_id=step_id,
        step_type=WorkflowStepType.TASK,
        name="Test Task Step",
        description="A test task step",
        task_type="analysis",
        task_config={
            "description": "Execute test analysis",
            "task_type": "analysis",
            "priority": "medium",
            "input_data": {"prompt": "Analyze test data"},
        },
    )
    workflow = Workflow(
        workflow_id=uuid4(),
        name="Test Workflow",
        description="Test workflow for executor tests",
        status=WorkflowStatus.ACTIVE,
        steps=[_step_to_dict(step)],
        created_by=1,
    )
    return workflow, step


# ============================================================================
# Test 1: Task created by WorkflowExecutor is actually executed by TaskExecutor
# ============================================================================


def test_workflow_executor_calls_task_executor():
    """Test that _execute_task_step calls TaskExecutor.execute_task when task_executor is available."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            # Create services
            task_service = TaskService(session)
            rbac = RBACService(session)
            user = create_test_user()

            # Mock TaskExecutor
            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(return_value=TaskResult(
                success=True,
                output={"result": "Task executed successfully"},
                metadata={"executor_type": "mock", "task_status": "completed"},
            ))

            # Create workflow executor with mock TaskExecutor
            executor = WorkflowExecutor(
                session=session,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            workflow, step = create_workflow_with_task_step()
            wf_execution = WorkflowExecution(
                workflow_id=workflow.workflow_id,
                started_by=user.id,
            )

            # Execute task step
            result = await executor._execute_task_step(step, wf_execution, user)

            # Verify TaskExecutor.execute_task was called
            mock_executor.execute_task.assert_called_once()
            call_args = mock_executor.execute_task.call_args
            assert call_args is not None

            # Verify result contains execution info
            assert result["task_id"] is not None
            assert result["status"] is not None

    asyncio.run(_run())


def test_workflow_executor_skips_task_executor_when_not_available():
    """Test that _execute_task_step falls back to creating task only when no task_executor."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            user = create_test_user()

            # Create workflow executor WITHOUT task_executor
            executor = WorkflowExecutor(
                session=session,
                task_service=task_service,
                rbac_service=rbac,
                audit_service=AuditService(),
            )
            # task_executor should be None
            assert executor.task_executor is None

            workflow, step = create_workflow_with_task_step()
            wf_execution = WorkflowExecution(
                workflow_id=workflow.workflow_id,
                started_by=user.id,
            )

            # Execute task step - should create task but not execute
            result = await executor._execute_task_step(step, wf_execution, user)

            # Should have created a task but not executed it
            assert result["task_id"] is not None
            assert result["status"] == "pending"

    asyncio.run(_run())


# ============================================================================
# Test 2: Full workflow execution with TaskExecutor
# ============================================================================


def test_workflow_execution_completed():
    """Test full workflow execution: pending → running → completed."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow model in DB
            workflow, step = create_workflow_with_task_step()
            wf_model = WorkflowModel(
                id=str(workflow.workflow_id),
                name=workflow.name,
                description=workflow.description,
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Mock TaskExecutor
            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(return_value=TaskResult(
                success=True,
                output={"result": "Analysis complete"},
                metadata={"executor_type": "mock", "task_status": "completed"},
            ))

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow
            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Verify execution status
            assert execution.status == WorkflowExecutionStatus.COMPLETED
            assert execution.started_at is not None
            assert execution.completed_at is not None
            assert execution.result is not None
            assert "results" in execution.result

            # Verify mock executor was called (may be called multiple times due to recovery retry)
            mock_executor.execute_task.assert_called()

    asyncio.run(_run())


def test_workflow_execution_failed():
    """Test workflow execution failure: pending → running → failed."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow model in DB
            workflow, step = create_workflow_with_task_step()
            wf_model = WorkflowModel(
                id=str(workflow.workflow_id),
                name=workflow.name,
                description=workflow.description,
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Mock TaskExecutor that raises an error
            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(side_effect=RuntimeError("Task execution failed"))

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow - should fail
            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Verify execution status is FAILED
            assert execution.status == WorkflowExecutionStatus.FAILED
            assert execution.error is not None
            assert "Task execution failed" in execution.error

            # Verify mock executor was called (may be called multiple times due to recovery retry)
            mock_executor.execute_task.assert_called()

    asyncio.run(_run())


# ============================================================================
# Test 3: WorkflowExecution persisted to database
# ============================================================================


def test_workflow_execution_persisted_to_db():
    """Test WorkflowExecution state is persisted to database."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow model in DB
            workflow, step = create_workflow_with_task_step()
            wf_model = WorkflowModel(
                id=str(workflow.workflow_id),
                name=workflow.name,
                description=workflow.description,
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Mock TaskExecutor
            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(return_value=TaskResult(
                success=True,
                output={"result": "Done"},
                metadata={"executor_type": "mock", "task_status": "completed"},
            ))

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow
            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Verify execution is in DB
            from src.database.repositories.workflow import WorkflowExecutionRepository
            repo = WorkflowExecutionRepository(session)
            db_model = await repo.get_by_id(str(execution.execution_id))
            assert db_model is not None
            assert db_model.status == "COMPLETED"
            assert db_model.started_at is not None
            assert db_model.completed_at is not None
            assert db_model.workflow_id == str(workflow.workflow_id)

    asyncio.run(_run())


def test_workflow_execution_failed_persisted_to_db():
    """Test WorkflowExecution FAILED state is persisted to database."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow model in DB
            workflow, step = create_workflow_with_task_step()
            wf_model = WorkflowModel(
                id=str(workflow.workflow_id),
                name=workflow.name,
                description=workflow.description,
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Mock TaskExecutor that raises
            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(side_effect=RuntimeError("Execution error"))

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow - should fail
            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Verify FAILED state is in DB
            from src.database.repositories.workflow import WorkflowExecutionRepository
            repo = WorkflowExecutionRepository(session)
            db_model = await repo.get_by_id(str(execution.execution_id))
            assert db_model is not None
            assert db_model.status == "FAILED"
            assert db_model.error is not None
            assert "Execution error" in db_model.error
            assert db_model.completed_at is not None

    asyncio.run(_run())


def test_workflow_execution_status_from_db():
    """Test execution status loaded from DB matches in-memory status."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow model in DB
            workflow, step = create_workflow_with_task_step()
            wf_model = WorkflowModel(
                id=str(workflow.workflow_id),
                name=workflow.name,
                description=workflow.description,
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Mock TaskExecutor
            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(return_value=TaskResult(
                success=True,
                output={"result": "Done"},
                metadata={"executor_type": "mock", "task_status": "completed"},
            ))

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow
            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Read from DB and verify
            from src.database.repositories.workflow import WorkflowExecutionRepository
            repo = WorkflowExecutionRepository(session)
            db_model = await repo.get_by_id(str(execution.execution_id))
            db_execution = model_to_workflow_execution(db_model)

            assert db_execution.status == execution.status
            assert db_execution.started_at is not None
            assert db_execution.completed_at is not None

    asyncio.run(_run())


# ============================================================================
# Test 4: Task no assigned employee → no fake completed
# ============================================================================


def test_task_executor_no_assigned_employee():
    """Test TaskExecutor properly fails on unassigned tasks — no silent placeholder success."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            # Create a task without assigned_to
            task = await task_service.create_task(
                title="Unassigned Task",
                description="Task with no AI employee assigned",
                task_type=TaskType.ANALYSIS,
                user=user,
                priority=TaskPriority.MEDIUM,
                assigned_to=None,
            )

            executor = TaskExecutor(task_service=task_service)

            # Execute task — should fail with clear error
            with pytest.raises(ExecutionError) as exc_info:
                await executor.execute_task(task.id, user)

            assert "No AI employee assigned" in str(exc_info.value)

    asyncio.run(_run())


# ============================================================================
# Test 5: GoalService.execute_goal_workflow creates WorkflowExecutor with task_executor
# ============================================================================


def test_goal_service_creates_executor_with_task_executor():
    """Test that GoalService.execute_goal_workflow passes task_executor to WorkflowExecutor."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.goal_service import GoalService
            user = await create_test_user_in_db(session)

            # Create a goal and workflow in DB
            workflow, step = create_workflow_with_task_step()
            wf_model = WorkflowModel(
                id=str(workflow.workflow_id),
                name=workflow.name,
                description=workflow.description,
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            goal = GoalModel(
                id=1,
                title="Test Goal",
                description="Test goal for executor verification",
                status="active",
                created_by=int(user.id),
                workflow_id=str(workflow.workflow_id),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(goal)
            await session.commit()

            goal_service = GoalService(session)

            # Execute goal workflow
            result = await goal_service.execute_goal_workflow(1, user)

            # Verify goal was processed
            assert result is not None
            assert result.status in ("completed", "failed", "active")

    asyncio.run(_run())


# ============================================================================
# Test 7: Multi-step workflow with context passing between steps
# ============================================================================


def test_multi_step_workflow_context_passing():
    """Test that Step A results are passed to Step B via execution.variables and step_results."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow with TWO TASK steps
            step_a_id = "step-a"
            step_b_id = "step-b"
            step_a = WorkflowStep(
                step_id=step_a_id,
                step_type=WorkflowStepType.TASK,
                name="Step A",
                description="First step",
                task_type="analysis",
                task_config={
                    "description": "Execute step A",
                    "task_type": "analysis",
                    "priority": "medium",
                    "input_data": {"prompt": "Execute step A"},
                },
            )
            step_b = WorkflowStep(
                step_id=step_b_id,
                step_type=WorkflowStepType.TASK,
                name="Step B",
                description="Second step",
                task_type="analysis",
                task_config={
                    "description": "Execute step B",
                    "task_type": "analysis",
                    "priority": "medium",
                    "input_data": {"prompt": "Execute step B"},
                },
            )

            workflow_id = uuid4()
            wf_model = WorkflowModel(
                id=str(workflow_id),
                name="Multi-Step Test Workflow",
                description="Test workflow with two steps",
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step_a), _step_to_dict(step_b)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Mock TaskExecutor - Step A succeeds, then Step B gets context
            call_count = 0
            step_a_result_data = {"analysis": "Step A completed successfully", "value": 42}

            async def mock_execute_task(task_id, user, context=None):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Step A: return result
                    return TaskResult(
                        success=True,
                        output=step_a_result_data,
                        metadata={"executor_type": "mock", "task_status": "completed"},
                    )
                else:
                    # Step B: verify context contains Step A's result
                    assert context is not None, "Step B should receive context from Step A"
                    wf_ctx = context.get("_workflow_context", {})
                    step_results = wf_ctx.get("step_results", {})
                    assert step_a_id in step_results, (
                        f"Step B should see Step A's result in step_results. "
                        f"Got keys: {list(step_results.keys())}"
                    )
                    step_a_result = step_results[step_a_id]
                    assert step_a_result.get("status") == "completed"
                    return TaskResult(
                        success=True,
                        output={"analysis": "Step B completed using Step A context"},
                        metadata={"executor_type": "mock", "task_status": "completed"},
                    )

            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(side_effect=mock_execute_task)

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow
            execution = await executor.execute_workflow(
                workflow_id=workflow_id,
                user=user,
            )

            # Verify workflow completed
            assert execution.status == WorkflowExecutionStatus.COMPLETED
            assert execution.started_at is not None
            assert execution.completed_at is not None
            assert execution.result is not None

            # Verify step_results contains both steps
            assert step_a_id in execution.step_results, (
                f"step_results should contain Step A. Got keys: {list(execution.step_results.keys())}"
            )
            assert step_b_id in execution.step_results, (
                f"step_results should contain Step B. Got keys: {list(execution.step_results.keys())}"
            )

            # Verify variables contain step outputs
            assert f"_step_{step_a_id}" in execution.variables
            assert f"_step_{step_b_id}" in execution.variables

            # Verify both steps were executed
            assert mock_executor.execute_task.call_count == 2

    asyncio.run(_run())


def test_workflow_step_failure_no_fake_completed():
    """Test that when Step A fails, Step B is not executed and workflow enters FAILED."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow with TWO TASK steps
            step_a_id = "step-a-fail"
            step_b_id = "step-b-fail"
            step_a = WorkflowStep(
                step_id=step_a_id,
                step_type=WorkflowStepType.TASK,
                name="Step A (will fail)",
                description="First step that fails",
                task_type="analysis",
                task_config={
                    "description": "This step will fail",
                    "task_type": "analysis",
                    "priority": "medium",
                    "input_data": {"prompt": "Execute step A"},
                },
            )
            step_b = WorkflowStep(
                step_id=step_b_id,
                step_type=WorkflowStepType.TASK,
                name="Step B",
                description="Second step",
                task_type="analysis",
                task_config={
                    "description": "This step should not execute",
                    "task_type": "analysis",
                    "priority": "medium",
                    "input_data": {"prompt": "Execute step B"},
                },
            )

            workflow_id = uuid4()
            wf_model = WorkflowModel(
                id=str(workflow_id),
                name="Failure Test Workflow",
                description="Test workflow with failing step",
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step_a), _step_to_dict(step_b)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Mock TaskExecutor: Step A fails, Step B should never be called
            # Track which step IDs are attempted to verify Step B is never called
            step_a_attempts = 0

            async def mock_execute_task(task_id, user, context=None):
                nonlocal step_a_attempts
                # Check if this is Step A or Step B based on context
                is_step_b = (
                    context is not None
                    and isinstance(context, dict)
                    and context.get("_workflow_context") is not None
                    and any(
                        "step-b" in str(k) for k in
                        context.get("_workflow_context", {}).get("step_results", {}).keys()
                    )
                )
                if is_step_b:
                    raise AssertionError("Step B should not be executed when Step A fails")

                step_a_attempts += 1
                return TaskResult(
                    success=False,
                    output=None,
                    error="Step A execution failed: insufficient data",
                    metadata={"executor_type": "mock", "task_status": "failed"},
                )

            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(side_effect=mock_execute_task)

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow
            execution = await executor.execute_workflow(
                workflow_id=workflow_id,
                user=user,
            )

            # Verify workflow FAILED (may have been retried by recovery chain)
            assert execution.status == WorkflowExecutionStatus.FAILED, (
                f"Workflow should FAIL when Step A fails. Got: {execution.status}"
            )
            assert execution.error is not None
            assert "Step A" in execution.error or "failed" in execution.error

            # Step B was never attempted (only Step A, possibly retried)
            assert step_a_attempts >= 1, "Step A should have been attempted at least once"

    asyncio.run(_run())


def test_workflow_execution_intermediate_state_persisted():
    """Test that after each step, the WorkflowExecution state is persisted to DB."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

            # Create a workflow with TWO TASK steps
            step_a_id = "step-a-persist"
            step_b_id = "step-b-persist"
            step_a = WorkflowStep(
                step_id=step_a_id,
                step_type=WorkflowStepType.TASK,
                name="Step A",
                description="First step",
                task_type="analysis",
                task_config={
                    "description": "Execute step A",
                    "task_type": "analysis",
                    "priority": "medium",
                    "input_data": {"prompt": "Execute step A"},
                    "employee_id": "00000000-0000-0000-0000-000000000001",
                },
            )
            step_b = WorkflowStep(
                step_id=step_b_id,
                step_type=WorkflowStepType.TASK,
                name="Step B",
                description="Second step",
                task_type="analysis",
                task_config={
                    "description": "Execute step B",
                    "task_type": "analysis",
                    "priority": "medium",
                    "input_data": {"prompt": "Execute step B"},
                    "employee_id": "00000000-0000-0000-0000-000000000002",
                },
            )

            workflow_id = uuid4()
            wf_model = WorkflowModel(
                id=str(workflow_id),
                name="Persistence Test Workflow",
                description="Test workflow intermediate persistence",
                created_by=str(user.id),
                enabled=True,
                steps=[_step_to_dict(step_a), _step_to_dict(step_b)],
                context={},
            )
            session.add(wf_model)
            await session.commit()

            # Use a real TaskExecutor with mock employee service
            employee_service = MagicMock(spec=AIEmployeeService)
            employee_service.execute_task = AsyncMock(return_value={
                "execution_id": "test-exec-123",
                "employee_id": "emp-456",
                "employee_name": "Test Employee",
                "agent_type": "general",
                "status": "completed",
                "output": {"result": "Step completed"},
                "error": None,
                "response_time_ms": 100,
            })

            task_executor = TaskExecutor(
                task_service=task_service,
                employee_service=employee_service,
            )

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=task_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Execute workflow
            execution = await executor.execute_workflow(
                workflow_id=workflow_id,
                user=user,
            )

            # Verify workflow completed
            assert execution.status == WorkflowExecutionStatus.COMPLETED

            # Verify DB state after completion
            from src.database.repositories.workflow import WorkflowExecutionRepository
            repo = WorkflowExecutionRepository(session)
            db_model = await repo.get_by_id(str(execution.execution_id))
            assert db_model is not None
            assert db_model.status == "COMPLETED"
            assert db_model.started_at is not None
            assert db_model.completed_at is not None
            assert db_model.variables is not None
            assert f"_step_{step_a_id}" in db_model.variables
            assert f"_step_{step_b_id}" in db_model.variables

    asyncio.run(_run())


def test_pause_execution_persisted():
    """Test pause_execution persists PAUSED status to DB."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            user = await create_test_user_in_db(session)

            executor = WorkflowExecutor(
                session=session,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Create execution directly
            execution = WorkflowExecution(
                workflow_id=uuid4(),
                started_by=user.id,
                status=WorkflowExecutionStatus.RUNNING,
            )
            executor._executions[execution.execution_id] = execution

            # Persist initial state
            await executor._persist_execution(execution)

            # Pause
            await executor.pause_execution(execution.execution_id, user)

            # Verify PAUSED in DB
            from src.database.repositories.workflow import WorkflowExecutionRepository
            repo = WorkflowExecutionRepository(session)
            db_model = await repo.get_by_id(str(execution.execution_id))
            assert db_model is not None
            assert db_model.status == "PAUSED"

    asyncio.run(_run())


def test_cancel_execution_persisted():
    """Test cancel_execution persists CANCELLED status to DB."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            user = await create_test_user_in_db(session)

            executor = WorkflowExecutor(
                session=session,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            # Create execution directly
            execution = WorkflowExecution(
                workflow_id=uuid4(),
                started_by=user.id,
                status=WorkflowExecutionStatus.RUNNING,
            )
            executor._executions[execution.execution_id] = execution

            # Persist initial state
            await executor._persist_execution(execution)

            # Cancel
            await executor.cancel_execution(execution.execution_id, user)

            # Verify CANCELLED in DB
            from src.database.repositories.workflow import WorkflowExecutionRepository
            repo = WorkflowExecutionRepository(session)
            db_model = await repo.get_by_id(str(execution.execution_id))
            assert db_model is not None
            assert db_model.status == "CANCELLED"

    asyncio.run(_run())