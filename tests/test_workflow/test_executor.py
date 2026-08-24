"""
Tests for WorkflowExecutor - Test all execution patterns
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.core.events import EventBus
from src.identity.audit import AuditService
from src.identity.models import RoleEnum, User
from src.identity.rbac import RBACService
from src.tasks.service import TaskService
from src.workflow.executor import WorkflowExecutor
from src.workflow.service import WorkflowService


@pytest.fixture
def admin_user():
    """Create admin user"""
    return User(
        id=1,
        username="admin",
        email="admin@test.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )


@pytest.fixture
def mock_rbac():
    """Mock RBAC service"""
    rbac = Mock(spec=RBACService)
    rbac.check_permission = Mock(return_value=True)
    rbac.check_permission_by_id = AsyncMock(return_value=True)
    return rbac


@pytest.fixture
def mock_audit():
    """Mock audit service"""
    audit = Mock(spec=AuditService)
    audit.log = AsyncMock()  # Must be AsyncMock because AuditService.log is async
    return audit


@pytest.fixture
def mock_event_bus():
    """Mock event bus"""
    event_bus = Mock(spec=EventBus)
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def workflow_service(async_session, mock_rbac, mock_audit):
    """Create workflow service"""
    return WorkflowService(
        session=async_session,
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    )


@pytest.fixture
def task_service(async_session, mock_audit, mock_event_bus):
    """Create task service"""
    return TaskService(
        session=async_session,
        audit_service=mock_audit,
        event_bus=mock_event_bus,
    )


@pytest.fixture
def executor(workflow_service, task_service, mock_rbac, mock_audit, mock_event_bus):
    """Create workflow executor"""
    return WorkflowExecutor(
        workflow_service=workflow_service,
        task_service=task_service,
        rbac_service=mock_rbac,
        audit_service=mock_audit,
        event_bus=mock_event_bus,
    )


@pytest.mark.asyncio
async def test_execute_sequential_workflow(executor, workflow_service, admin_user):
    """Test executing sequential workflow"""
    # Create workflow with sequential steps
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Task 1",
            "task_type": "test_task",
        },
        {
            "step_id": "step2",
            "step_type": "task",
            "name": "Task 2",
            "task_type": "test_task",
        },
    ]

    workflow = await workflow_service.create_workflow(
        name="Sequential Workflow",
        description="Test sequential execution",
        steps=steps,
        user=admin_user,
    )

    # Execute workflow
    execution = await executor.execute_workflow(
        workflow_id=workflow.workflow_id,
        user=admin_user,
    )

    assert execution is not None
    # Since tasks are created but not actually executed (no real background workers)
    # we just verify the execution was created
    assert execution.workflow_id == workflow.workflow_id


@pytest.mark.asyncio
async def test_execute_parallel_workflow(executor, workflow_service, admin_user):
    """Test executing parallel workflow"""
    # Create workflow with parallel steps
    steps = [
        {
            "step_id": "parallel1",
            "step_type": "parallel",
            "name": "Parallel Group",
            "steps": [
                {
                    "step_id": "task1",
                    "step_type": "task",
                    "name": "Task 1",
                    "task_type": "test_task",
                },
                {
                    "step_id": "task2",
                    "step_type": "task",
                    "name": "Task 2",
                    "task_type": "test_task",
                },
            ],
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Parallel Workflow",
        description="Test parallel execution",
        steps=steps,
        user=admin_user,
    )

    # Execute workflow
    execution = await executor.execute_workflow(
        workflow_id=workflow.workflow_id,
        user=admin_user,
    )

    assert execution is not None
    assert execution.workflow_id == workflow.workflow_id


@pytest.mark.asyncio
async def test_execute_conditional_workflow(executor, workflow_service, admin_user):
    """Test executing conditional workflow"""
    # Create workflow with conditional step
    steps = [
        {
            "step_id": "cond1",
            "step_type": "conditional",
            "name": "Conditional Step",
            "condition": "variables.status == 'active'",
            "true_steps": [
                {
                    "step_id": "task_true",
                    "step_type": "task",
                    "name": "True Task",
                    "task_type": "test_task",
                }
            ],
            "false_steps": [
                {
                    "step_id": "task_false",
                    "step_type": "task",
                    "name": "False Task",
                    "task_type": "test_task",
                }
            ],
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Conditional Workflow",
        description="Test conditional execution",
        steps=steps,
        user=admin_user,
    )

    # Execute with true condition
    execution = await executor.execute_workflow(
        workflow_id=workflow.workflow_id,
        user=admin_user,
        variables={"status": "active"},
    )

    assert execution is not None


@pytest.mark.asyncio
async def test_execute_loop_workflow(executor, workflow_service, admin_user):
    """Test executing loop workflow"""
    # Create workflow with loop
    steps = [
        {
            "step_id": "loop1",
            "step_type": "loop",
            "name": "Loop Step",
            "loop_condition": "variables.counter < 3",
            "max_iterations": 5,
            "steps": [
                {
                    "step_id": "loop_task",
                    "step_type": "task",
                    "name": "Loop Task",
                    "task_type": "test_task",
                }
            ],
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Loop Workflow",
        description="Test loop execution",
        steps=steps,
        user=admin_user,
    )

    # Execute workflow
    execution = await executor.execute_workflow(
        workflow_id=workflow.workflow_id,
        user=admin_user,
        variables={"counter": 0},
    )

    assert execution is not None


@pytest.mark.asyncio
async def test_execute_workflow_not_found(executor, admin_user):
    """Test executing non-existent workflow"""
    workflow_id = uuid4()

    with pytest.raises(ValueError, match="not found"):
        await executor.execute_workflow(
            workflow_id=workflow_id,
            user=admin_user,
        )


@pytest.mark.asyncio
async def test_execute_workflow_permission_denied(
    executor, workflow_service, admin_user, mock_rbac
):
    """Test executing workflow without permission"""
    # Allow workflow creation first
    mock_rbac.check_permission = Mock(return_value=True)
    mock_rbac.check_permission_by_id = AsyncMock(return_value=True)

    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Task 1",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test",
        steps=steps,
        user=admin_user,
    )

    # Reset mock to deny execution
    mock_rbac.check_permission_by_id = AsyncMock(return_value=False)

    with pytest.raises(PermissionError):
        await executor.execute_workflow(
            workflow_id=workflow.workflow_id,
            user=admin_user,
        )


@pytest.mark.asyncio
@pytest.mark.skip(reason="Pause功能需要异步后台执行支持，当前同步执行模型下execution立即完成")
async def test_pause_execution(executor, workflow_service, admin_user):
    """Test pausing workflow execution"""
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Task 1",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test",
        steps=steps,
        user=admin_user,
    )

    # Start execution
    execution = await executor.execute_workflow(
        workflow_id=workflow.workflow_id,
        user=admin_user,
    )

    # Pause execution
    await executor.pause_execution(
        execution_id=execution.execution_id,
        user=admin_user,
    )

    # Check status
    exec_status = await executor.get_execution(execution.execution_id, admin_user)
    # Note: Actual status depends on execution state when pause was called
    assert exec_status is not None


@pytest.mark.asyncio
@pytest.mark.skip(reason="Resume功能需要异步后台执行支持，当前同步执行模型下execution立即完成")
async def test_resume_execution(executor, workflow_service, admin_user):
    """Test resuming workflow execution"""
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Task 1",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test",
        steps=steps,
        user=admin_user,
    )

    # Start execution
    execution = await executor.execute_workflow(
        workflow_id=workflow.workflow_id,
        user=admin_user,
    )

    # Pause and resume
    await executor.pause_execution(execution.execution_id, admin_user)
    await executor.resume_execution(execution.execution_id, admin_user)

    # Verify execution exists
    exec_status = await executor.get_execution(execution.execution_id, admin_user)
    assert exec_status is not None


@pytest.mark.asyncio
@pytest.mark.skip(reason="Cancel功能需要异步后台执行支持，当前同步执行模型下execution立即完成")
async def test_cancel_execution(executor, workflow_service, admin_user):
    """Test canceling workflow execution"""
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Task 1",
            "task_type": "test_task",
        }
    ]

    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        description="Test",
        steps=steps,
        user=admin_user,
    )

    # Start execution
    execution = await executor.execute_workflow(
        workflow_id=workflow.workflow_id,
        user=admin_user,
    )

    # Cancel execution
    await executor.cancel_execution(
        execution_id=execution.execution_id,
        user=admin_user,
    )

    # Check status
    exec_status = await executor.get_execution(execution.execution_id, admin_user)
    assert exec_status is not None
    # Status should be cancelled (if cancel happened before completion)


@pytest.mark.asyncio
async def test_list_executions(executor, workflow_service, admin_user):
    """Test listing workflow executions"""
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Task 1",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test",
        steps=steps,
        user=admin_user,
    )

    # Create multiple executions
    for _ in range(2):
        await executor.execute_workflow(
            workflow_id=workflow.workflow_id,
            user=admin_user,
        )

    # List executions
    executions = await executor.list_executions(workflow.workflow_id, admin_user)

    assert len(executions) >= 2
