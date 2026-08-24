"""
Tests for Task models and service
"""

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from src.core.errors import NotFoundError
from src.core.events import EventBus
from src.identity.audit import AuditService
from src.identity.models import RoleEnum, User
from src.tasks.models import TaskPriority, TaskStatus, TaskType
from src.tasks.service import TaskService


@pytest.fixture
def admin_user():
    """Create admin user"""
    return User(
        id=UUID("12345678-1234-1234-1234-123456789012"),
        username="admin",
        email="admin@test.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )


@pytest.fixture
def mock_audit():
    """Mock audit service"""
    audit = AsyncMock(spec=AuditService)
    audit.log = AsyncMock()
    return audit


@pytest.fixture
def mock_event_bus():
    """Mock event bus"""
    event_bus = AsyncMock(spec=EventBus)
    event_bus.publish = AsyncMock()
    return event_bus


@pytest_asyncio.fixture
async def task_service(async_session, mock_audit, mock_event_bus):
    """Create task service"""
    return TaskService(
        session=async_session,
        audit_service=mock_audit,
        event_bus=mock_event_bus,
    )


@pytest.mark.asyncio
async def test_create_task(task_service, admin_user):
    """Test creating task"""
    task = await task_service.create_task(
        title="Test Task",
        description="Test Description",
        task_type=TaskType.GENERAL,
        user=admin_user,
        priority=TaskPriority.MEDIUM,
    )

    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.task_type == TaskType.GENERAL
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.MEDIUM
    assert task.creator_id == admin_user.id


@pytest.mark.asyncio
async def test_get_task(task_service, admin_user):
    """Test getting task"""
    # Create task
    task = await task_service.create_task(
        title="Test Task",
        description="Test Description",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    # Get task
    retrieved = await task_service.get_task(task.id, admin_user)

    assert retrieved is not None
    assert retrieved.id == task.id
    assert retrieved.title == "Test Task"


@pytest.mark.asyncio
async def test_get_task_not_found(task_service, admin_user):
    """Test getting non-existent task"""
    task_id = uuid4()

    with pytest.raises(NotFoundError):
        await task_service.get_task(task_id, admin_user)


@pytest.mark.asyncio
async def test_list_tasks(task_service, admin_user):
    """Test listing tasks"""
    # Create multiple tasks
    for i in range(3):
        await task_service.create_task(
            title=f"Task {i}",
            description=f"Description {i}",
            task_type=TaskType.GENERAL,
            user=admin_user,
        )

    # List tasks
    tasks = await task_service.list_tasks(admin_user)

    assert len(tasks) >= 3


@pytest.mark.asyncio
async def test_list_tasks_by_status(task_service, admin_user):
    """Test listing tasks by status"""
    # Create tasks with different statuses
    task1 = await task_service.create_task(
        title="Task 1",
        description="Description 1",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    task2 = await task_service.create_task(
        title="Task 2",
        description="Description 2",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    # Update one task status
    await task_service.update_task_status(
        task_id=task1.id,
        status=TaskStatus.RUNNING,
        user=admin_user,
    )

    # List pending tasks
    pending_tasks = await task_service.list_tasks(admin_user, status=TaskStatus.PENDING)

    assert any(t.id == task2.id for t in pending_tasks)
    assert not any(t.id == task1.id for t in pending_tasks)


@pytest.mark.asyncio
async def test_update_task_status(task_service, admin_user):
    """Test updating task status"""
    # Create task
    task = await task_service.create_task(
        title="Test Task",
        description="Test Description",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    # Update status
    await task_service.update_task_status(
        task_id=task.id,
        status=TaskStatus.RUNNING,
        user=admin_user,
    )

    # Verify update
    updated = await task_service.get_task(task.id, admin_user)
    assert updated.status == TaskStatus.RUNNING


@pytest.mark.asyncio
async def test_complete_task(task_service, admin_user):
    """Test completing task"""
    # Create task
    task = await task_service.create_task(
        title="Test Task",
        description="Test Description",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    # Complete task
    await task_service.complete_task(
        task_id=task.id,
        result={"output": "success"},
        user=admin_user,
    )

    # Verify completion
    completed = await task_service.get_task(task.id, admin_user)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.result.success
    assert completed.result.output == {"output": "success"}


@pytest.mark.asyncio
async def test_fail_task(task_service, admin_user):
    """Test failing task"""
    # Create task
    task = await task_service.create_task(
        title="Test Task",
        description="Test Description",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    # Fail task
    await task_service.fail_task(
        task_id=task.id,
        error="Test error",
        user=admin_user,
    )

    # Verify failure
    failed = await task_service.get_task(task.id, admin_user)
    assert failed.status == TaskStatus.FAILED
    assert failed.error == "Test error"


@pytest.mark.asyncio
async def test_assign_task(task_service, admin_user):
    """Test assigning task"""
    # Create task
    task = await task_service.create_task(
        title="Test Task",
        description="Test Description",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    # Assign task
    assigned_to_id = UUID("22345678-1234-1234-1234-123456789012")
    await task_service.assign_task(
        task_id=task.id,
        agent_ids=[assigned_to_id],
        user=admin_user,
    )

    # Verify assignment
    assigned = await task_service.get_task(task.id, admin_user)
    assert assigned.assigned_to == [assigned_to_id]


@pytest.mark.asyncio
async def test_delete_task(task_service, admin_user):
    """Test deleting task"""
    # Create task
    task = await task_service.create_task(
        title="Test Task",
        description="Test Description",
        task_type=TaskType.GENERAL,
        user=admin_user,
    )

    # Delete task
    await task_service.delete_task(task.id, admin_user)

    # Verify deletion
    with pytest.raises(NotFoundError):
        await task_service.get_task(task.id, admin_user)
