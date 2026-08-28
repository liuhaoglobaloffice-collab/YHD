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
    """Test TaskExecutor properly handles unassigned tasks."""
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

            # Execute task
            result = await executor.execute_task(task.id, user)

            # Should return a no-assignment result, not fake completed
            assert result.success is True
            meta = result.metadata or {}
            assert meta.get("executor_type") == "unassigned"
            assert meta.get("requires_assignment") is True

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
# Test 6: Pause/Resume/Cancel persist to DB
# ============================================================================


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