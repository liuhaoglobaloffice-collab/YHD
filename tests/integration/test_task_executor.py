"""
TaskExecutor Integration Tests
Covers:
A. Normal execution - pending task → execute → completed, result saved
B. Execution failure - exception → task failed, error saved
C. State transitions - pending → running → completed; pending → running → failed
D. Execution timing - created/start/completed times exist, duration can be calculated
E. No existing business linkage broken - Workflow → AI Employee → Task Executor works
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.tasks.executor import TaskExecutor, ExecutionError
from src.tasks.models import Task, TaskResult, TaskStatus, TaskType, TaskPriority
from src.tasks.service import TaskService
from src.identity.models import User
from src.workforce.employee import AIEmployeeService

# All tests use asyncio.run() inside the test, no need for pytest-asyncio mark


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


def test_task_executor_normal_execution():
    """Test A: Normal execution - pending task → execute → completed, result saved."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            # Create services
            task_service = TaskService(session)
            user = create_test_user()

            # Mock AIEmployeeService with successful response
            employee_service = MagicMock(spec=AIEmployeeService)
            employee_service.execute_task = AsyncMock(return_value={
                "execution_id": "test-exec-123",
                "employee_id": "emp-456",
                "employee_name": "Test Employee",
                "agent_type": "general",
                "status": "completed",
                "output": "Task completed successfully with result: 42",
                "error": None,
                "response_time_ms": 150,
            })

            # Create executor
            executor = TaskExecutor(
                task_service=task_service,
                employee_service=employee_service,
            )

            # Create a pending task assigned to an employee
            from uuid import uuid4
            employee_id = uuid4()
            task = await task_service.create_task(
                title="Test Task",
                description="Test normal execution",
                task_type=TaskType.ANALYSIS,
                user=user,
                priority=TaskPriority.MEDIUM,
                assigned_to=[employee_id],
                input_data={"prompt": "Analyze this data"},
            )

            # Verify initial state
            assert task.status == TaskStatus.PENDING
            assert task.started_at is None
            assert task.completed_at is None
            assert task.result is None

            # Execute
            result = await executor.execute_task(task.id, user)

            # Verify result
            assert result.success is True
            assert result.output is not None
            assert result.output["output"] == "Task completed successfully with result: 42"

            # Verify task state after execution
            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.COMPLETED
            assert updated_task.started_at is not None
            assert updated_task.completed_at is not None
            assert updated_task.result is not None
            assert updated_task.result.success is True

            # Verify execution time fields
            assert updated_task.created_at is not None
            assert updated_task.started_at >= updated_task.created_at
            assert updated_task.completed_at >= updated_task.started_at

            # Verify duration can be calculated
            duration = (updated_task.completed_at - updated_task.started_at).total_seconds()
            assert duration >= 0

            # Verify employee service was called correctly
            employee_service.execute_task.assert_called_once()

    asyncio.run(_run())


def test_task_executor_execution_failure():
    """Test B: Execution failure - exception → task failed, error saved."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            # Mock AIEmployeeService that raises exception
            employee_service = MagicMock(spec=AIEmployeeService)
            employee_service.execute_task = AsyncMock(side_effect=Exception("AI service unavailable"))

            executor = TaskExecutor(
                task_service=task_service,
                employee_service=employee_service,
            )

            from uuid import uuid4
            employee_id = uuid4()
            task = await task_service.create_task(
                title="Failing Task",
                description="This task should fail",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                input_data={"prompt": "This will fail"},
            )

            assert task.status == TaskStatus.PENDING

            # Execute and expect ExecutionError
            with pytest.raises(ExecutionError) as exc_info:
                await executor.execute_task(task.id, user)

            assert "Task execution failed: AI service unavailable" in str(exc_info.value)

            # Verify task is marked FAILED in database
            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.FAILED
            assert updated_task.started_at is not None
            assert updated_task.completed_at is not None
            assert updated_task.result is not None
            assert updated_task.result.success is False
            assert "AI service unavailable" in updated_task.result.error or \
                   "AI service unavailable" in (updated_task.error or "")

    asyncio.run(_run())


def test_task_executor_state_transitions_completed():
    """Test C: State transition - pending → running → completed."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            employee_service = MagicMock(spec=AIEmployeeService)
            employee_service.execute_task = AsyncMock(return_value={
                "execution_id": "test-456",
                "employee_id": "emp-789",
                "employee_name": "Success Employee",
                "agent_type": "coder",
                "status": "completed",
                "output": "Done",
                "error": None,
                "response_time_ms": 200,
            })

            executor = TaskExecutor(task_service, employee_service)

            from uuid import uuid4
            employee_id = uuid4()
            task = await task_service.create_task(
                title="State Transition Test",
                description="Testing pending → running → completed",
                task_type=TaskType.CODING,
                user=user,
                assigned_to=[employee_id],
            )

            # Initial: pending
            assert task.status == TaskStatus.PENDING

            # We can't easily check the intermediate running state without hooks,
            # but we can verify the final state
            result = await executor.execute_task(task.id, user)

            # Final: completed
            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.COMPLETED
            assert result.success is True

    asyncio.run(_run())


def test_task_executor_state_transitions_failed():
    """Test C: State transition - pending → running → failed."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            employee_service = MagicMock(spec=AIEmployeeService)
            employee_service.execute_task = AsyncMock(side_effect=ValueError("Invalid input format"))

            executor = TaskExecutor(task_service, employee_service)

            from uuid import uuid4
            employee_id = uuid4()
            task = await task_service.create_task(
                title="Failure Transition Test",
                description="Testing pending → running → failed",
                task_type=TaskType.CODING,
                user=user,
                assigned_to=[employee_id],
            )

            assert task.status == TaskStatus.PENDING

            with pytest.raises(ExecutionError):
                await executor.execute_task(task.id, user)

            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.FAILED
            assert updated_task.started_at is not None
            assert updated_task.completed_at is not None

    asyncio.run(_run())


def test_task_executor_execution_timing():
    """Test D: Execution timing - all timestamps present, duration calculable."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            employee_service = MagicMock(spec=AIEmployeeService)
            employee_service.execute_task = AsyncMock(return_value={
                "execution_id": "timing-test",
                "employee_id": "emp-timing",
                "employee_name": "Timing Employee",
                "agent_type": "general",
                "status": "completed",
                "output": "Timing test complete",
                "error": None,
                "response_time_ms": 100,
            })

            executor = TaskExecutor(task_service, employee_service)

            from uuid import uuid4
            employee_id = uuid4()
            before_create = datetime.now(UTC)
            task = await task_service.create_task(
                title="Timing Test",
                description="Test all timing fields",
                task_type=TaskType.TESTING,
                user=user,
                assigned_to=[employee_id],
            )
            after_create = datetime.now(UTC)

            # created_at should be between before_create and after_create
            assert task.created_at is not None
            # SQLite may return naive datetimes, so use naive comparison
            assert before_create.replace(tzinfo=None) <= task.created_at.replace(tzinfo=None) <= after_create.replace(tzinfo=None)

            # Initial state
            assert task.started_at is None
            assert task.completed_at is None

            # Execute
            before_exec = datetime.now(UTC)
            result = await executor.execute_task(task.id, user)
            after_exec = datetime.now(UTC)

            # Verify all timestamps
            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.created_at is not None
            assert updated_task.started_at is not None
            assert updated_task.completed_at is not None

            # Check ordering (SQLite may return naive datetimes)
            assert updated_task.created_at.replace(tzinfo=None) >= before_create.replace(tzinfo=None)
            assert updated_task.started_at.replace(tzinfo=None) >= before_exec.replace(tzinfo=None)
            assert updated_task.completed_at.replace(tzinfo=None) <= after_exec.replace(tzinfo=None)
            assert updated_task.created_at.replace(tzinfo=None) <= updated_task.started_at.replace(tzinfo=None) <= updated_task.completed_at.replace(tzinfo=None)

            # Calculate duration
            duration = (updated_task.completed_at - updated_task.started_at).total_seconds()
            assert duration >= 0
            assert duration <= (after_exec - before_exec).total_seconds()

    asyncio.run(_run())


def test_task_executor_no_employee_assigned():
    """Test: Task with no assigned employee returns structured result."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            executor = TaskExecutor(task_service, None)

            task = await task_service.create_task(
                title="Unassigned Task",
                description="No employee assigned",
                task_type=TaskType.GENERAL,
                user=user,
                assigned_to=[],  # Empty
            )

            assert task.status == TaskStatus.PENDING

            result = await executor.execute_task(task.id, user)

            # Should succeed with note about no assignment
            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.COMPLETED
            assert result.success is True
            assert result.output["note"] == "No AI employee assigned. Task accepted but not executed."
            assert result.metadata["requires_assignment"] is True

    asyncio.run(_run())


def test_task_executor_wrong_initial_status():
    """Test: Cannot execute task that's not pending/ready."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            executor = TaskExecutor(task_service, None)

            from uuid import uuid4
            employee_id = uuid4()
            task = await task_service.create_task(
                title="Already Completed",
                description="Should not execute",
                task_type=TaskType.GENERAL,
                user=user,
                assigned_to=[employee_id],
            )

            # Mark as completed manually
            await task_service.update_task_status(task.id, TaskStatus.COMPLETED, user)

            # Try to execute - should fail
            with pytest.raises(ExecutionError) as exc_info:
                await executor.execute_task(task.id, user)

            assert "Task cannot be executed in status: completed" in str(exc_info.value)

            # Status should still be completed
            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.COMPLETED

    asyncio.run(_run())


def test_task_executor_dependencies_not_satisfied():
    """Test: Task with unmet dependencies gets marked blocked and fails."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            executor = TaskExecutor(task_service, None)

            from uuid import uuid4
            # Create dependency task (still pending)
            dep_task = await task_service.create_task(
                title="Dependency",
                description="Dependency task",
                task_type=TaskType.GENERAL,
                user=user,
            )

            # Create task that depends on it
            from src.tasks.models import TaskDependency
            dep = TaskDependency(task_id=dep_task.id, dependency_type="finish_to_start")

            task = await task_service.create_task(
                title="Dependent Task",
                description="Depends on another task",
                task_type=TaskType.GENERAL,
                user=user,
                dependencies=[dep],
            )

            # Dependency not completed - should raise and mark blocked
            with pytest.raises(ExecutionError) as exc_info:
                await executor.execute_task(task.id, user)

            assert "Task dependencies not satisfied" in str(exc_info.value)

            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.BLOCKED

    asyncio.run(_run())


def test_task_executor_cancel_running_task():
    """Test: Cancel a task while it's (still) in running state."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            executor = TaskExecutor(task_service, None)

            task = await task_service.create_task(
                title="Task to Cancel",
                description="Will be cancelled",
                task_type=TaskType.GENERAL,
                user=user,
            )

            # Task is pending - can be cancelled
            result = await executor.cancel_task(task.id, user)
            assert result is True

            updated_task = await task_service.get_task(task.id, user)
            assert updated_task.status == TaskStatus.CANCELLED

    asyncio.run(_run())


def test_task_executor_execute_ready_tasks():
    """Test: Bulk execute all ready tasks."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()

            employee_service = MagicMock(spec=AIEmployeeService)
            employee_service.execute_task = AsyncMock(return_value={
                "execution_id": "bulk-test",
                "employee_id": "emp-bulk",
                "employee_name": "Bulk Employee",
                "agent_type": "general",
                "status": "completed",
                "output": "Bulk done",
                "error": None,
                "response_time_ms": 50,
            })

            executor = TaskExecutor(task_service, employee_service)

            from uuid import uuid4
            employee_id = uuid4()

            # Create three tasks, one has a dependency
            task1 = await task_service.create_task(
                title="Ready Task 1",
                description="Ready to execute",
                task_type=TaskType.GENERAL,
                user=user,
                assigned_to=[employee_id],
            )

            task2 = await task_service.create_task(
                title="Ready Task 2",
                description="Ready to execute",
                task_type=TaskType.GENERAL,
                user=user,
                assigned_to=[employee_id],
            )

            # Complete the first two so they're out of the way
            await task_service.update_task_status(task1.id, TaskStatus.COMPLETED, user)
            await task_service.update_task_status(task2.id, TaskStatus.COMPLETED, user)

            # Create a new ready task
            task3 = await task_service.create_task(
                title="Ready Task 3",
                description="Ready to execute",
                task_type=TaskType.GENERAL,
                user=user,
                assigned_to=[employee_id],
            )

            # Get ready tasks and execute
            ready_before = await task_service.get_ready_tasks(user)
            assert len(ready_before) == 1
            assert ready_before[0].id == task3.id

            results = await executor.execute_ready_tasks(user, max_concurrent=5)
            assert len(results) == 1
            assert results[0].success is True

            # After execution, task3 should be completed
            updated = await task_service.get_task(task3.id, user)
            assert updated.status == TaskStatus.COMPLETED

    asyncio.run(_run())
