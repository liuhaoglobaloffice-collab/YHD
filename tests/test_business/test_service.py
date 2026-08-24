"""
Tests for Business Service
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.agents import AgentType
from src.business.models import (
    BusinessDomain,
    BusinessTaskPriority,
    BusinessTaskStatus,
)
from src.business.registry import BusinessTaskRegistry
from src.business.service import BusinessService
from src.core.errors import PermissionDeniedError, ValidationError
from src.identity.audit import AuditService
from src.identity.rbac import Permission, RBACService
from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position
from src.workforce.registry import AIEmployeeRegistry


@pytest_asyncio.fixture
async def task_registry(async_session: AsyncSession):
    """Business task registry fixture"""
    return BusinessTaskRegistry(async_session)


@pytest_asyncio.fixture
async def employee_registry(async_session: AsyncSession):
    """AI employee registry fixture"""
    registry = AIEmployeeRegistry(async_session)

    # Add a test employee
    employee = AIEmployee(
        name="Test Employee",
        department=Department.MARKETING,
        position=Position.MARKETING_SPECIALIST,
        description="Test employee",
        agent_type=AgentType.GPT,  # Add required agent_type
        status=AIEmployeeStatus.ACTIVE,
    )
    await registry.register(employee)

    return registry


@pytest.fixture
def rbac_service():
    """Mock RBAC service fixture"""
    service = AsyncMock(spec=RBACService)
    service.check_permission_by_id = AsyncMock(
        return_value=True
    )  # BusinessService uses check_permission_by_id
    service.session = AsyncMock()  # Add session attribute for audit.log
    return service


@pytest.fixture
def audit_service():
    """Mock audit service fixture"""
    service = AsyncMock(spec=AuditService)
    return service


@pytest_asyncio.fixture
async def business_service(task_registry, employee_registry, rbac_service, audit_service):
    """Business service fixture"""
    return BusinessService(task_registry, employee_registry, rbac_service, audit_service)


@pytest.mark.asyncio
async def test_create_task(business_service, rbac_service, audit_service):
    """Test creating a business task"""
    user_id = uuid4()

    task = await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Test Task",
        description="Test Description",
        priority=BusinessTaskPriority.HIGH,
        tags=["test"],
    )

    assert task.id is not None
    assert task.domain == BusinessDomain.MARKETING
    assert task.title == "Test Task"
    assert task.status == BusinessTaskStatus.CREATED
    assert "test" in task.tags

    # Verify RBAC was checked
    rbac_service.check_permission_by_id.assert_called_once_with(user_id, Permission.TASK_CREATE)

    # Verify audit was logged
    audit_service.log.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_without_permission(business_service, rbac_service):
    """Test creating task without permission fails"""
    user_id = uuid4()
    rbac_service.check_permission_by_id = AsyncMock(return_value=False)

    with pytest.raises(PermissionDeniedError):
        await business_service.create_task(
            user_id=user_id,
            domain=BusinessDomain.MARKETING,
            title="Test",
            description="Test",
        )


@pytest.mark.asyncio
async def test_create_task_validation(business_service):
    """Test task creation validation"""
    user_id = uuid4()

    # Missing title
    with pytest.raises(ValidationError, match="title is required"):
        await business_service.create_task(
            user_id=user_id,
            domain=BusinessDomain.MARKETING,
            title="",
            description="Test",
        )

    # Missing description
    with pytest.raises(ValidationError, match="description is required"):
        await business_service.create_task(
            user_id=user_id,
            domain=BusinessDomain.MARKETING,
            title="Test",
            description="",
        )


@pytest.mark.asyncio
async def test_assign_task(business_service, employee_registry):
    """Test assigning task to employee"""
    user_id = uuid4()

    # Create task
    task = await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Test",
        description="Test",
    )

    # Get employee
    employees = await employee_registry.list_employees()
    employee = employees[0]

    # Assign task
    assigned_task = await business_service.assign_task(
        user_id=user_id,
        task_id=task.id,
        employee_id=employee.id,
    )

    assert assigned_task.status == BusinessTaskStatus.ASSIGNED
    assert assigned_task.assigned_employee_id == employee.id
    assert assigned_task.assigned_by == user_id
    assert assigned_task.assigned_at is not None


@pytest.mark.asyncio
async def test_start_task(business_service, employee_registry):
    """Test starting a task"""
    user_id = uuid4()

    # Create and assign task
    task = await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Test",
        description="Test",
    )

    employees = await employee_registry.list_employees()
    employee = employees[0]

    task = await business_service.assign_task(user_id, task.id, employee.id)

    # Start task
    started_task = await business_service.start_task(user_id, task.id)

    assert started_task.status == BusinessTaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_complete_task(business_service, employee_registry):
    """Test completing a task"""
    user_id = uuid4()

    # Create, assign, and start task
    task = await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Test",
        description="Test",
    )

    employees = await employee_registry.list_employees()
    employee = employees[0]

    task = await business_service.assign_task(user_id, task.id, employee.id)
    task = await business_service.start_task(user_id, task.id)

    # Complete task
    result = {"output": "Success"}
    completed_task = await business_service.complete_task(user_id, task.id, result=result)

    assert completed_task.status == BusinessTaskStatus.COMPLETED
    assert completed_task.result == result
    assert completed_task.completed_at is not None


@pytest.mark.asyncio
async def test_fail_task(business_service, employee_registry):
    """Test marking task as failed"""
    user_id = uuid4()

    # Create, assign, and start task
    task = await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Test",
        description="Test",
    )

    employees = await employee_registry.list_employees()
    employee = employees[0]

    task = await business_service.assign_task(user_id, task.id, employee.id)
    task = await business_service.start_task(user_id, task.id)

    # Fail task
    error_msg = "Task execution failed"
    failed_task = await business_service.fail_task(user_id, task.id, error=error_msg)

    assert failed_task.status == BusinessTaskStatus.FAILED
    assert failed_task.error == error_msg
    assert failed_task.completed_at is not None


@pytest.mark.asyncio
async def test_get_task(business_service):
    """Test getting a task"""
    user_id = uuid4()

    # Create task
    task = await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Test",
        description="Test",
    )

    # Get task
    retrieved = await business_service.get_task(user_id, task.id)

    assert retrieved.id == task.id
    assert retrieved.title == task.title


@pytest.mark.asyncio
async def test_list_tasks(business_service):
    """Test listing tasks"""
    user_id = uuid4()

    # Create multiple tasks
    await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Task 1",
        description="Desc 1",
    )
    await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.SALES,
        title="Task 2",
        description="Desc 2",
    )

    # List all tasks
    all_tasks = await business_service.list_tasks(user_id)
    assert len(all_tasks) == 2

    # List filtered by domain
    marketing_tasks = await business_service.list_tasks(user_id, domain=BusinessDomain.MARKETING)
    assert len(marketing_tasks) == 1
    assert marketing_tasks[0].domain == BusinessDomain.MARKETING


@pytest.mark.asyncio
async def test_get_domain_metrics(business_service, employee_registry):
    """Test getting domain metrics"""
    user_id = uuid4()

    # Create tasks
    task1 = await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Task 1",
        description="Desc 1",
    )

    await business_service.create_task(
        user_id=user_id,
        domain=BusinessDomain.MARKETING,
        title="Task 2",
        description="Desc 2",
    )

    # Complete one task
    employees = await employee_registry.list_employees()
    employee = employees[0]

    task1 = await business_service.assign_task(user_id, task1.id, employee.id)
    task1 = await business_service.start_task(user_id, task1.id)
    await business_service.complete_task(user_id, task1.id)

    # Get metrics
    metrics = await business_service.get_domain_metrics(user_id, BusinessDomain.MARKETING)

    assert metrics.domain == BusinessDomain.MARKETING
    assert metrics.total_tasks == 2
    assert metrics.completed_tasks == 1
    assert metrics.in_progress_tasks == 0
    assert metrics.success_rate == 1.0
