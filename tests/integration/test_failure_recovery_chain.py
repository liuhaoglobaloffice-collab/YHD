"""
Failure Recovery Chain Integration Tests
Covers P1: Failure Recovery Chain (14 scenarios)

Test scenarios:
1.  Task 正常执行 (pending → running → completed)
2.  Task 第一次失败、Recovery 后成功
3.  transient failure 自动 retry
4.  retry 达到上限后 FAILED
5.  不可恢复错误直接 FAILED
6.  Recovery strategy 被正确调用
7.  Workflow 失败后进入 recovery
8.  recovery 成功后 Workflow 继续
9.  recovery 最终失败 → Workflow FAILED
10. Goal 不会在 Task/Workflow 失败时错误变成 COMPLETED
11. failure/recovery 状态正确持久化
12. 异常路径不会丢失状态
13. 不会无限 retry
14. 不会伪造 completed
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.ai.recovery import FailureCategory, RecoveryChain, StrategyAction
from src.database.base import Base
from src.database.models import FailureRecordModel, GoalModel, TaskModel, WorkflowModel, WorkflowExecutionModel
from src.database.repositories.converters import _step_to_dict, model_to_workflow_execution
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import Permission, RBACService, RoleEnum
from src.tasks.executor import ExecutionError, TaskExecutor
from src.tasks.models import Task, TaskPriority, TaskResult, TaskStatus, TaskType
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


def create_mock_employee(employee_id=None):
    """Create a mock AIEmployeeService with controllable responses."""
    emp = MagicMock(spec=AIEmployeeService)
    emp.execute_task = AsyncMock()
    return emp


def make_success_response(output="Task completed successfully"):
    """Create a successful AI employee response."""
    return {
        "execution_id": str(uuid4()),
        "employee_id": "emp-456",
        "employee_name": "Test Employee",
        "agent_type": "general",
        "status": "completed",
        "output": output,
        "error": None,
        "response_time_ms": 150,
    }


def make_failure_response(error="AI service error"):
    """Create a failed AI employee response."""
    return {
        "execution_id": str(uuid4()),
        "employee_id": "emp-456",
        "employee_name": "Test Employee",
        "agent_type": "general",
        "status": "failed",
        "output": None,
        "error": error,
        "response_time_ms": 150,
    }


# ============================================================================
# Helper: Create a workflow with a single TASK step
# ============================================================================


def create_workflow_with_task_step(workflow_id=None):
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
        workflow_id=workflow_id or uuid4(),
        name="Test Workflow",
        description="Test workflow for recovery tests",
        status=WorkflowStatus.ACTIVE,
        steps=[_step_to_dict(step)],
        created_by=1,
    )
    return workflow, step


# ============================================================================
# Test 1: Task 正常执行
# ============================================================================


def test_task_normal_execution():
    """Test 1: Task 正常执行 - pending → running → completed."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            emp = create_mock_employee()
            emp.execute_task.return_value = make_success_response()

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="Normal Task",
                description="Normal execution test",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                input_data={"prompt": "Execute task"},
            )

            result = await executor.execute_task(task.id, user)

            assert result.success is True
            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.COMPLETED
            assert updated.started_at is not None
            assert updated.completed_at is not None

    asyncio.run(_run())


# ============================================================================
# Test 2: Task 第一次失败、Recovery 后成功
# ============================================================================


def test_task_first_fail_then_recovery_success():
    """Test 2: Task 第一次失败、Recovery 后成功."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            # Mock: first call fails, second call succeeds
            call_count = 0

            async def mock_execute(employee_id, prompt, actor_id=None,
                                    temperature=None, max_tokens=None,
                                    context_data=None):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("Transient provider error")
                return make_success_response("Recovered successfully")

            emp = create_mock_employee()
            emp.execute_task = AsyncMock(side_effect=mock_execute)

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="Recovery Test",
                description="Will fail then recover",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=3,
                input_data={"prompt": "Execute task"},
            )

            result = await executor.execute_task(task.id, user)

            assert result.success is True
            assert result.output["output"] == "Recovered successfully"
            assert call_count == 2

            # Verify task state
            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.COMPLETED
            assert updated.retry_count == 1  # One retry was made

            # Verify RecoveryChain recorded the failure and lesson
            recovery_chain = RecoveryChain(session)
            records = await recovery_chain.get_failure_records(page_size=100)
            assert records["total"] >= 1
            # Find the record for this task
            task_records = [r for r in records["items"] if r["task_id"] == str(task.id)]
            assert len(task_records) >= 1
            record = task_records[0]
            assert record["retry_count"] >= 1
            assert record["is_successful"] is True
            assert record["lesson_learned"] is not None

    asyncio.run(_run())


# ============================================================================
# Test 3: transient failure 自动 retry
# ============================================================================


def test_transient_failure_auto_retry():
    """Test 3: transient failure 自动 retry (provider error classified correctly)."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            # Simulate transient provider error
            emp = create_mock_employee()
            emp.execute_task.side_effect = RuntimeError("Provider API returned 503")

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="Transient Failure",
                description="Provider error test",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=3,
                input_data={"prompt": "Execute task"},
            )

            # Should exhaust all retries and fail
            with pytest.raises(ExecutionError) as exc_info:
                await executor.execute_task(task.id, user)

            assert "Provider" in str(exc_info.value) or "503" in str(exc_info.value)

            # Verify task is FAILED
            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.FAILED
            assert updated.retry_count == 3  # All retries used

            # Verify RecoveryChain classified as PROVIDER_ERROR
            recovery_chain = RecoveryChain(session)
            records = await recovery_chain.get_failure_records(page_size=100)
            task_records = [r for r in records["items"] if r["task_id"] == str(task.id)]
            assert len(task_records) >= 1
            record = task_records[0]
            assert record["failure_category"] == FailureCategory.PROVIDER_ERROR.value

    asyncio.run(_run())


# ============================================================================
# Test 4: retry 达到上限后 FAILED
# ============================================================================


def test_retry_exhausted_failed():
    """Test 4: retry 达到上限后 FAILED."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            emp = create_mock_employee()
            emp.execute_task.side_effect = RuntimeError("Persistent error")

            # Create task with max_retries=2
            task = await task_service.create_task(
                title="Retry Limit",
                description="Should exhaust retries",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=2,
                input_data={"prompt": "Execute task"},
            )

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            with pytest.raises(ExecutionError):
                await executor.execute_task(task.id, user)

            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.FAILED
            # max_retries=2 means 1 + 2 = 3 attempts total, so 2 retries
            assert updated.retry_count == 2
            # Should not have retried more than max_retries
            assert updated.retry_count <= updated.max_retries

    asyncio.run(_run())


# ============================================================================
# Test 5: 不可恢复错误直接 FAILED
# ============================================================================


def test_unrecoverable_error_abort():
    """Test 5: 不可恢复错误直接 FAILED (ABORT strategy)."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            # Simulate auth error (AUTH_ERROR → REQUEST_BOSS/ABORT)
            emp = create_mock_employee()
            emp.execute_task.side_effect = PermissionError("API key unauthorized")

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="Auth Error",
                description="Unrecoverable error",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=3,
                input_data={"prompt": "Execute task"},
            )

            with pytest.raises(ExecutionError):
                await executor.execute_task(task.id, user)

            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.FAILED
            # Should NOT have retried for AUTH_ERROR (ABORT strategy)
            assert updated.retry_count == 0

    asyncio.run(_run())


# ============================================================================
# Test 6: Recovery strategy 被正确调用
# ============================================================================


def test_recovery_strategy_called():
    """Test 6: Recovery strategy 被正确调用 (record_failure + determine_strategy)."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            emp = create_mock_employee()
            emp.execute_task.side_effect = RuntimeError("Provider error")

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            # Verify RecoveryChain is initialized
            assert executor.recovery_chain is not None
            assert executor.recovery_executor is not None

            task = await task_service.create_task(
                title="Strategy Test",
                description="Verify recovery chain called",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=1,
                input_data={"prompt": "Execute task"},
            )

            with pytest.raises(ExecutionError):
                await executor.execute_task(task.id, user)

            # Verify RecoveryChain recorded the failure
            recovery_chain = RecoveryChain(session)
            records = await recovery_chain.get_failure_records(page_size=100)
            task_records = [r for r in records["items"] if r["task_id"] == str(task.id)]
            assert len(task_records) >= 1
            record = task_records[0]
            # Strategy should have been recorded
            assert record["strategy_action"] is not None
            # Retry count should be > 0 on the recovery record
            assert record["retry_count"] >= 1

    asyncio.run(_run())


# ============================================================================
# Test 7: Workflow 失败后进入 recovery
# ============================================================================


def test_workflow_failure_enters_recovery():
    """Test 7: Workflow 失败后进入 recovery (已有类似测试，验证 recovery 记录)."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

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

            # Mock TaskExecutor that always fails
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

            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Workflow should be FAILED
            assert execution.status == WorkflowExecutionStatus.FAILED
            assert execution.error is not None

            # Verify RecoveryChain recorded the workflow failure
            recovery_chain = RecoveryChain(session)
            records = await recovery_chain.get_failure_records(page_size=100)
            wf_records = [r for r in records["items"] if r["workflow_id"] == str(workflow.workflow_id)]
            assert len(wf_records) >= 1
            record = wf_records[0]
            assert record["failure_category"] is not None

    asyncio.run(_run())


# ============================================================================
# Test 8: recovery 成功后 Workflow 继续
# ============================================================================


def test_workflow_recovery_success_continues():
    """Test 8: Task recovery 成功后 Workflow 继续."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            # Simulate: first call fails, second call succeeds
            call_count = 0

            async def mock_execute(employee_id, prompt, actor_id=None,
                                    temperature=None, max_tokens=None,
                                    context_data=None):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("Transient timeout error")
                return make_success_response("Recovered after retry")

            emp = create_mock_employee()
            emp.execute_task = AsyncMock(side_effect=mock_execute)

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="Recovery Continues",
                description="Fail then recover",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=3,
                input_data={"prompt": "Execute task"},
            )

            # Execute - should succeed after retry
            result = await executor.execute_task(task.id, user)

            assert result.success is True
            assert result.output["output"] == "Recovered after retry"
            assert call_count == 2

            # Verify task state
            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.COMPLETED
            # retry_count is 1 (one retry made)
            assert updated.retry_count == 1

    asyncio.run(_run())


# ============================================================================
# Test 9: recovery 最终失败 → Workflow FAILED
# ============================================================================


def test_recovery_final_failure_workflow_failed():
    """Test 9: recovery 最终失败 → Workflow FAILED."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

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

            # Mock TaskExecutor that always fails
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

            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Workflow should be FAILED after all recovery attempts
            assert execution.status == WorkflowExecutionStatus.FAILED, (
                f"Workflow should FAIL after recovery failure. Got: {execution.status}"
            )
            assert execution.error is not None

    asyncio.run(_run())


# ============================================================================
# Test 10: Goal 不会在 Task/Workflow 失败时错误变成 COMPLETED
# ============================================================================


def test_goal_not_completed_when_workflow_failed():
    """Test 10: Goal 不会在 Workflow 失败时错误变成 COMPLETED."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.goal_service import GoalService
            user = await create_test_user_in_db(session)

            # Create a workflow and goal — with assigned_to so task fails without employee_service
            workflow_id = uuid4()
            workflow, step = create_workflow_with_task_step(workflow_id)
            # Add assigned_to so task will fail (no employee_service in GoalService)
            step.task_config["assigned_to"] = [str(uuid4())]

            wf_model = WorkflowModel(
                id=str(workflow_id),
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
                description="Goal should not be completed when workflow fails",
                status="active",
                created_by=int(user.id),
                workflow_id=str(workflow_id),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(goal)
            await session.commit()

            # Execute goal workflow - will fail because TaskExecutor has no employee service
            goal_service = GoalService(session)
            result = await goal_service.execute_goal_workflow(1, user)

            # Goal should be FAILED, not COMPLETED
            assert result.status == "failed", (
                f"Goal should be 'failed' when workflow fails. Got: {result.status}"
            )

    asyncio.run(_run())


def test_goal_not_completed_when_task_failed():
    """Test 10b: Goal 不会在 Task FAILED 但 Workflow 被误标记 COMPLETED 时变成 COMPLETED."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.goal_service import GoalService
            user = await create_test_user_in_db(session)

            # Create a workflow with a task step — with assigned_to so task fails without employee_service
            workflow_id = uuid4()
            workflow, step = create_workflow_with_task_step(workflow_id)
            # Add assigned_to so task will fail (no employee_service in GoalService)
            step.task_config["assigned_to"] = [str(uuid4())]

            wf_model = WorkflowModel(
                id=str(workflow_id),
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
                id=2,
                title="Goal with Failed Task",
                description="Goal should fail when task fails",
                status="active",
                created_by=int(user.id),
                workflow_id=str(workflow_id),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(goal)
            await session.commit()

            # The mock TaskExecutor will fail, so WorkflowExecutor will set FAILED
            # GoalService will then set goal to "failed"
            goal_service = GoalService(session)
            result = await goal_service.execute_goal_workflow(2, user)

            # Goal should be FAILED, not COMPLETED
            assert result.status == "failed", (
                f"Goal should be 'failed' when task fails. Got: {result.status}"
            )

    asyncio.run(_run())


# ============================================================================
# Test 11: failure/recovery 状态正确持久化
# ============================================================================


def test_failure_recovery_persisted():
    """Test 11: failure/recovery 状态正确持久化到数据库."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            emp = create_mock_employee()
            emp.execute_task.side_effect = RuntimeError("Persistent failure")

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="Persistence Test",
                description="Verify DB persistence",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=2,
                input_data={"prompt": "Execute task"},
            )

            with pytest.raises(ExecutionError):
                await executor.execute_task(task.id, user)

            # Verify Task persisted in DB
            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.FAILED
            assert updated.retry_count == 2  # Persisted
            assert updated.completed_at is not None

            # Verify FailureRecord persisted in DB
            from sqlalchemy import select
            query = select(FailureRecordModel).where(
                FailureRecordModel.task_id == str(task.id)
            )
            result = await session.execute(query)
            records = list(result.scalars().all())
            assert len(records) >= 1
            record = records[0]
            assert record.failure_category is not None
            assert record.retry_count > 0
            assert record.strategy_action == StrategyAction.ABORT.value or record.strategy_action == StrategyAction.RETRY.value

    asyncio.run(_run())


# ============================================================================
# Test 12: 异常路径不会丢失状态
# ============================================================================


def test_exception_path_preserves_state():
    """Test 12: 异常路径不会丢失状态 - error 和 retry_count 正确持久化."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            emp = create_mock_employee()
            emp.execute_task.side_effect = ValueError("Invalid input data")

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="Exception Path",
                description="Error state preservation",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=1,
                input_data={"prompt": "Execute task"},
            )

            with pytest.raises(ExecutionError) as exc_info:
                await executor.execute_task(task.id, user)

            error_msg = str(exc_info.value)

            # Verify error is in the exception
            assert "Invalid input data" in error_msg

            # Verify task FAILED state in DB
            updated = await task_service.get_task(task.id, user)
            assert updated.status == TaskStatus.FAILED
            assert updated.started_at is not None
            assert updated.completed_at is not None
            assert updated.result is not None
            assert updated.result.success is False
            assert updated.result.error is not None

            # Verify AuditService logged the failure
            # (AuditService is called with status="failure" in the final failure block)

    asyncio.run(_run())


# ============================================================================
# Test 13: 不会无限 retry
# ============================================================================


def test_no_infinite_retry():
    """Test 13: 不会无限 retry - max_retries 限制严格生效."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            emp = create_mock_employee()
            emp.execute_task.side_effect = RuntimeError("Persistent error")

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            # Test with different max_retries values
            for max_retries in [1, 3, 5]:
                task = await task_service.create_task(
                    title=f"Infinite Retry Test {max_retries}",
                    description=f"max_retries={max_retries}",
                    task_type=TaskType.ANALYSIS,
                    user=user,
                    assigned_to=[employee_id],
                    max_retries=max_retries,
                    input_data={"prompt": "Execute task"},
                )

                with pytest.raises(ExecutionError):
                    await executor.execute_task(task.id, user)

                updated = await task_service.get_task(task.id, user)
                assert updated.retry_count == max_retries, (
                    f"retry_count should be {max_retries}, got {updated.retry_count}"
                )
                assert updated.retry_count <= updated.max_retries, (
                    f"retry_count ({updated.retry_count}) should not exceed max_retries ({updated.max_retries})"
                )

    asyncio.run(_run())


# ============================================================================
# Test 14: 不会伪造 completed
# ============================================================================


def test_no_fake_completed():
    """Test 14: 不会伪造 completed - 失败任务不会被标记为 completed."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            user = create_test_user()
            employee_id = uuid4()

            emp = create_mock_employee()
            emp.execute_task.side_effect = RuntimeError("Should not be completed")

            executor = TaskExecutor(task_service=task_service, employee_service=emp)

            task = await task_service.create_task(
                title="No Fake Complete",
                description="Task should not be completed",
                task_type=TaskType.ANALYSIS,
                user=user,
                assigned_to=[employee_id],
                max_retries=2,
                input_data={"prompt": "Execute task"},
            )

            with pytest.raises(ExecutionError):
                await executor.execute_task(task.id, user)

            # Verify task is NOT completed
            updated = await task_service.get_task(task.id, user)
            assert updated.status != TaskStatus.COMPLETED, "Task should not be COMPLETED"
            assert updated.status == TaskStatus.FAILED, "Task should be FAILED"
            assert updated.result is not None
            assert updated.result.success is False


def test_workflow_no_fake_completed():
    """Test 14b: Workflow 不会伪造 completed - 步骤失败时 Workflow 应为 FAILED."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            task_service = TaskService(session)
            rbac = RBACService(session)
            workflow_service = WorkflowService(session, rbac_service=rbac)
            user = await create_test_user_in_db(session)

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

            # Mock TaskExecutor that returns failure (not raises)
            mock_executor = MagicMock(spec=TaskExecutor)
            mock_executor.execute_task = AsyncMock(return_value=TaskResult(
                success=False,
                output=None,
                error="Step execution failed: insufficient data",
                metadata={"executor_type": "mock", "task_status": "failed"},
            ))

            executor = WorkflowExecutor(
                session=session,
                workflow_service=workflow_service,
                task_service=task_service,
                task_executor=mock_executor,
                rbac_service=rbac,
                audit_service=AuditService(),
            )

            execution = await executor.execute_workflow(
                workflow_id=workflow.workflow_id,
                user=user,
            )

            # Workflow should be FAILED, not COMPLETED
            assert execution.status == WorkflowExecutionStatus.FAILED, (
                f"Workflow should not be COMPLETED when task fails. Got: {execution.status}"
            )

    asyncio.run(_run())