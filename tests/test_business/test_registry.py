"""
Tests for Business Task Registry
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.models import (
    BusinessDomain,
    BusinessTask,
    BusinessTaskPriority,
    BusinessTaskStatus,
)
from src.business.registry import BusinessTaskRegistry
from src.core.errors import ResourceNotFoundError, ValidationError


@pytest_asyncio.fixture
async def registry(async_session: AsyncSession):
    """Business task registry fixture"""
    return BusinessTaskRegistry(async_session)


@pytest.fixture
def sample_task():
    """Sample business task fixture"""
    return BusinessTask(
        domain=BusinessDomain.MARKETING,
        title="Test Task",
        description="Test Description",
        priority=BusinessTaskPriority.MEDIUM,
    )


@pytest.mark.asyncio
async def test_registry_initialization(registry):
    """Test registry initializes with session"""
    assert registry.session is not None
    assert registry.repo is not None


@pytest.mark.asyncio
async def test_register_task(registry, sample_task):
    """Test registering a task"""
    registered = await registry.register(sample_task)

    assert registered.id == sample_task.id
    assert registered.title == sample_task.title


@pytest.mark.asyncio
async def test_register_duplicate_task(registry, sample_task):
    """Test registering duplicate task fails"""
    await registry.register(sample_task)

    with pytest.raises(ValidationError, match="already exists"):
        await registry.register(sample_task)


@pytest.mark.asyncio
async def test_get_task(registry, sample_task):
    """Test getting a task by ID"""
    await registry.register(sample_task)

    retrieved = await registry.get(sample_task.id)

    assert retrieved.id == sample_task.id
    assert retrieved.title == sample_task.title


@pytest.mark.asyncio
async def test_get_nonexistent_task(registry):
    """Test getting nonexistent task fails"""
    task_id = uuid4()

    with pytest.raises(ResourceNotFoundError):
        await registry.get(task_id)


@pytest.mark.asyncio
async def test_update_task(registry, sample_task):
    """Test updating a task"""
    await registry.register(sample_task)

    sample_task.title = "Updated Title"
    sample_task.status = BusinessTaskStatus.IN_PROGRESS

    updated = await registry.update(sample_task.id, sample_task)

    assert updated.title == "Updated Title"
    assert updated.status == BusinessTaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_update_nonexistent_task(registry, sample_task):
    """Test updating nonexistent task fails"""
    with pytest.raises(ResourceNotFoundError):
        await registry.update(uuid4(), sample_task)


@pytest.mark.asyncio
async def test_delete_task(registry, sample_task):
    """Test deleting a task"""
    await registry.register(sample_task)

    # Verify it exists
    task = await registry.get(sample_task.id)
    assert task is not None

    await registry.delete(sample_task.id)

    # Verify deletion
    with pytest.raises(ResourceNotFoundError):
        await registry.get(sample_task.id)


@pytest.mark.asyncio
async def test_delete_nonexistent_task(registry):
    """Test deleting nonexistent task fails"""
    with pytest.raises(ResourceNotFoundError):
        await registry.delete(uuid4())


@pytest.mark.asyncio
async def test_list_all_tasks(registry):
    """Test listing all tasks"""
    task1 = BusinessTask(
        domain=BusinessDomain.MARKETING,
        title="Task 1",
        description="Description 1",
    )
    task2 = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Task 2",
        description="Description 2",
    )

    await registry.register(task1)
    await registry.register(task2)

    tasks = await registry.list()

    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_list_tasks_by_domain(registry):
    """Test filtering tasks by domain"""
    task1 = BusinessTask(domain=BusinessDomain.MARKETING, title="Task 1", description="Desc 1")
    task2 = BusinessTask(domain=BusinessDomain.SALES, title="Task 2", description="Desc 2")
    task3 = BusinessTask(domain=BusinessDomain.MARKETING, title="Task 3", description="Desc 3")

    await registry.register(task1)
    await registry.register(task2)
    await registry.register(task3)

    marketing_tasks = await registry.list(domain=BusinessDomain.MARKETING)

    assert len(marketing_tasks) == 2
    assert all(t.domain == BusinessDomain.MARKETING for t in marketing_tasks)


@pytest.mark.asyncio
async def test_list_tasks_by_status(registry):
    """Test filtering tasks by status"""
    task1 = BusinessTask(domain=BusinessDomain.MARKETING, title="Task 1", description="Desc 1")
    task2 = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Task 2",
        description="Desc 2",
        status=BusinessTaskStatus.IN_PROGRESS,
    )

    await registry.register(task1)
    await registry.register(task2)

    in_progress_tasks = await registry.list(status=BusinessTaskStatus.IN_PROGRESS)

    assert len(in_progress_tasks) == 1
    assert in_progress_tasks[0].status == BusinessTaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_list_tasks_by_priority(registry):
    """Test filtering tasks by priority"""
    task1 = BusinessTask(
        domain=BusinessDomain.MARKETING,
        title="Task 1",
        description="Desc 1",
        priority=BusinessTaskPriority.HIGH,
    )
    task2 = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Task 2",
        description="Desc 2",
        priority=BusinessTaskPriority.LOW,
    )

    await registry.register(task1)
    await registry.register(task2)

    high_priority_tasks = await registry.list(priority=BusinessTaskPriority.HIGH)

    assert len(high_priority_tasks) == 1
    assert high_priority_tasks[0].priority == BusinessTaskPriority.HIGH


@pytest.mark.asyncio
async def test_list_tasks_by_assigned_employee(registry):
    """Test filtering tasks by assigned employee"""
    employee_id = uuid4()

    task1 = BusinessTask(
        domain=BusinessDomain.MARKETING,
        title="Task 1",
        description="Desc 1",
        assigned_employee_id=employee_id,
    )
    task2 = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Task 2",
        description="Desc 2",
    )

    await registry.register(task1)
    await registry.register(task2)

    employee_tasks = await registry.list(assigned_employee_id=employee_id)

    assert len(employee_tasks) == 1
    assert employee_tasks[0].assigned_employee_id == employee_id


@pytest.mark.asyncio
async def test_count_by_status(registry):
    """Test counting tasks by status"""
    task1 = BusinessTask(domain=BusinessDomain.MARKETING, title="Task 1", description="Desc 1")
    task2 = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Task 2",
        description="Desc 2",
        status=BusinessTaskStatus.IN_PROGRESS,
    )
    task3 = BusinessTask(
        domain=BusinessDomain.OPERATIONS,
        title="Task 3",
        description="Desc 3",
        status=BusinessTaskStatus.COMPLETED,
    )

    await registry.register(task1)
    await registry.register(task2)
    await registry.register(task3)

    counts = await registry.count_by_status()

    assert counts["created"] == 1
    assert counts["in_progress"] == 1
    assert counts["completed"] == 1


@pytest.mark.asyncio
async def test_count_by_domain(registry):
    """Test counting tasks by domain"""
    task1 = BusinessTask(domain=BusinessDomain.MARKETING, title="Task 1", description="Desc 1")
    task2 = BusinessTask(domain=BusinessDomain.SALES, title="Task 2", description="Desc 2")
    task3 = BusinessTask(domain=BusinessDomain.MARKETING, title="Task 3", description="Desc 3")

    await registry.register(task1)
    await registry.register(task2)
    await registry.register(task3)

    counts = await registry.count_by_domain()

    assert counts["marketing"] == 2
    assert counts["sales"] == 1
    assert counts["operations"] == 0


@pytest.mark.asyncio
async def test_get_employee_tasks(registry):
    """Test getting all tasks for an employee"""
    employee_id = uuid4()

    task1 = BusinessTask(
        domain=BusinessDomain.MARKETING,
        title="Task 1",
        description="Desc 1",
        assigned_employee_id=employee_id,
    )
    task2 = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Task 2",
        description="Desc 2",
        assigned_employee_id=employee_id,
    )
    task3 = BusinessTask(domain=BusinessDomain.OPERATIONS, title="Task 3", description="Desc 3")

    await registry.register(task1)
    await registry.register(task2)
    await registry.register(task3)

    employee_tasks = await registry.get_employee_tasks(employee_id)

    assert len(employee_tasks) == 2
    assert all(t.assigned_employee_id == employee_id for t in employee_tasks)
