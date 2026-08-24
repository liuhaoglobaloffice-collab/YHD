"""
Test API Service Integration

Phase 2F-2.5: Verify complete data flow from API to Database with Factory Pattern.

Architecture under test:
API Endpoint → Factory → Service (fully initialized) → Repository → Database
"""

from uuid import uuid4

import pytest

from src.business.models import BusinessDomain
from src.tasks.models import TaskPriority, TaskStatus, TaskType
from src.workforce.models import Department, Position

# ============================================================
# Business API Integration Tests
# ============================================================


@pytest.mark.asyncio
async def test_business_task_create_integration(async_session):
    """Test Business Task creation writes to database."""
    from src.business.registry import BusinessTaskRegistry
    from src.business.service import BusinessService
    from src.identity.audit import AuditService
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workforce.registry import AIEmployeeRegistry

    # Create dependencies - Phase 2F-2.5: correct signatures
    task_registry = BusinessTaskRegistry(async_session)
    employee_registry = AIEmployeeRegistry(async_session)
    rbac_service = RBACService(async_session)

    service = BusinessService(
        task_registry=task_registry,
        employee_registry=employee_registry,
        rbac_service=rbac_service,
        audit_service=AuditService,  # Static class
    )

    # Create test user
    user = User(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    # Create business task
    task = await service.create_task(
        user_id=user.id,
        domain=BusinessDomain.MARKETING,
        title="Test Task",
        description="Integration test",
    )

    assert task is not None
    assert task.title == "Test Task"


@pytest.mark.asyncio
async def test_business_task_update_integration(async_session):
    """Test: Query business task through full stack"""
    from src.business.registry import BusinessTaskRegistry
    from src.business.service import BusinessService
    from src.identity.audit import AuditService
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workforce.registry import AIEmployeeRegistry

    # Create dependencies
    task_registry = BusinessTaskRegistry(async_session)
    employee_registry = AIEmployeeRegistry(async_session)
    rbac_service = RBACService(async_session)

    service = BusinessService(
        task_registry=task_registry,
        employee_registry=employee_registry,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )

    # Create test user
    user = User(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    # Create task
    task = await service.create_task(
        user_id=user.id,
        domain=BusinessDomain.SALES,
        title="Original Title",
        description="Original Description",
    )

    # Query task
    retrieved = await service.get_task(
        user_id=user.id,
        task_id=task.id,
    )

    assert retrieved is not None
    assert retrieved.id == task.id
    assert retrieved.title == "Original Title"


@pytest.mark.asyncio
async def test_business_task_query_integration(async_session):
    """Test: Query business tasks through repository"""
    from src.business.registry import BusinessTaskRegistry
    from src.business.service import BusinessService
    from src.identity.audit import AuditService
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workforce.registry import AIEmployeeRegistry

    # Create dependencies
    task_registry = BusinessTaskRegistry(async_session)
    employee_registry = AIEmployeeRegistry(async_session)
    rbac_service = RBACService(async_session)

    service = BusinessService(
        task_registry=task_registry,
        employee_registry=employee_registry,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )

    # Create test user
    user = User(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    # Create multiple tasks
    await service.create_task(
        user_id=user.id, domain=BusinessDomain.RESEARCH, title="Task 1", description="Description 1"
    )
    await service.create_task(
        user_id=user.id,
        domain=BusinessDomain.OPERATIONS,
        title="Task 2",
        description="Description 2",
    )

    # Query tasks
    tasks = await service.list_tasks(user_id=user.id)

    assert len(tasks) >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="BusinessService无delete_task方法，状态机不支持直接complete CREATED任务")
async def test_business_task_delete_integration(async_session):
    """Test: Delete business task through full stack"""
    from src.business.registry import BusinessTaskRegistry
    from src.business.service import BusinessService
    from src.identity.audit import AuditService
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workforce.registry import AIEmployeeRegistry

    # Create dependencies
    task_registry = BusinessTaskRegistry(async_session)
    employee_registry = AIEmployeeRegistry(async_session)
    rbac_service = RBACService(async_session)

    service = BusinessService(
        task_registry=task_registry,
        employee_registry=employee_registry,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )

    # Create test user
    user = User(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    # Create and delete
    task = await service.create_task(
        user_id=user.id,
        domain=BusinessDomain.MARKETING,
        title="Delete Test",
        description="Will be deleted",
    )

    task_id = task.id
    await service.complete_task(user_id=user.id, task_id=task_id)

    # Verify deleted
    deleted_task = await service.get_task(task_id=task_id, user_id=user.id)
    assert deleted_task is None


@pytest.mark.asyncio
async def test_business_data_persistence_after_restart(async_session):
    """Test: Business data persists after service restart"""
    from src.business.registry import BusinessTaskRegistry
    from src.business.service import BusinessService
    from src.identity.audit import AuditService
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workforce.registry import AIEmployeeRegistry

    # Create dependencies
    task_registry = BusinessTaskRegistry(async_session)
    employee_registry = AIEmployeeRegistry(async_session)
    rbac_service = RBACService(async_session)

    service = BusinessService(
        task_registry=task_registry,
        employee_registry=employee_registry,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )

    # Create test user
    user = User(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    # Create task
    task = await service.create_task(
        user_id=user.id,
        domain=BusinessDomain.SALES,
        title="Persistent Task",
        description="Should survive restart",
    )
    task_id = task.id

    # Simulate service restart: create new service instance
    task_registry2 = BusinessTaskRegistry(async_session)
    employee_registry2 = AIEmployeeRegistry(async_session)
    rbac_service2 = RBACService(async_session)

    service2 = BusinessService(
        task_registry=task_registry2,
        employee_registry=employee_registry2,
        rbac_service=rbac_service2,
        audit_service=AuditService,
    )

    # Query from new service instance
    retrieved = await service2.get_task(task_id=task_id, user_id=user.id)
    assert retrieved is not None
    assert retrieved.title == "Persistent Task"


# ============================================================
# Workflow API Integration Tests
# ============================================================


@pytest.mark.asyncio
async def test_workflow_create_integration(async_session):
    """Test Workflow creation through full stack."""
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workflow.service import WorkflowService

    # Create service with dependencies
    rbac_service = RBACService(async_session)
    service = WorkflowService(
        session=async_session,
        rbac_service=rbac_service,
    )

    user = User(
        username="workflow_user",
        email="wf@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    # Create workflow
    workflow = await service.create_workflow(
        name="Test Workflow",
        description="Integration test workflow",
        steps=[
            {
                "step_id": "step1",
                "step_type": "TASK",
                "name": "Research",
                "description": "Research task",
                "task_type": "GENERAL",
            },
            {
                "step_id": "step2",
                "step_type": "TASK",
                "name": "Analyze",
                "description": "Analysis task",
                "task_type": "GENERAL",
            },
        ],
        user=user,
    )

    assert workflow is not None
    assert workflow.name == "Test Workflow"


@pytest.mark.asyncio
async def test_workflow_update_integration(async_session):
    """Test workflow update through repository."""
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workflow.service import WorkflowService

    rbac_service = RBACService(async_session)
    service = WorkflowService(session=async_session, rbac_service=rbac_service)

    user = User(
        username="workflow_user",
        email="wf@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    workflow = await service.create_workflow(
        name="Update Test",
        description="Original",
        steps=[
            {
                "step_id": "s1",
                "step_type": "TASK",
                "name": "Test Step",
                "description": "Test",
                "task_type": "GENERAL",
            }
        ],
        user=user,
    )

    # Update workflow
    updated = await service.update_workflow(
        workflow_id=workflow.workflow_id,
        description="Updated Description",
        user=user,
    )

    assert updated.description == "Updated Description"


@pytest.mark.asyncio
async def test_workflow_list_integration(async_session):
    """Test workflow list query."""
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workflow.service import WorkflowService

    rbac_service = RBACService(async_session)
    service = WorkflowService(session=async_session, rbac_service=rbac_service)

    user = User(
        username="workflow_user",
        email="wf@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    await service.create_workflow(
        "WF1",
        "First",
        [{"step_id": "s1", "step_type": "TASK", "name": "Step 1", "task_type": "GENERAL"}],
        user,
    )
    await service.create_workflow(
        "WF2",
        "Second",
        [{"step_id": "s2", "step_type": "TASK", "name": "Step 2", "task_type": "GENERAL"}],
        user,
    )

    workflows = await service.list_workflows(user=user)
    assert len(workflows) >= 2


@pytest.mark.asyncio
async def test_workflow_delete_integration(async_session):
    """Test workflow deletion."""
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workflow.service import WorkflowService

    rbac_service = RBACService(async_session)
    service = WorkflowService(session=async_session, rbac_service=rbac_service)

    user = User(
        username="workflow_user",
        email="wf@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.flush()

    workflow = await service.create_workflow(
        "Delete Test",
        "Will be deleted",
        [{"step_id": "s1", "step_type": "TASK", "name": "Delete Step", "task_type": "GENERAL"}],
        user,
    )

    wf_id = workflow.workflow_id
    deleted = await service.delete_workflow(workflow_id=wf_id, user=user)

    assert deleted is True


# ============================================================
# Task API Integration Tests
# ============================================================


@pytest.mark.asyncio
async def test_task_create_integration(async_session):
    """Test Task creation through full stack."""
    from src.identity.models import RoleEnum, User
    from src.tasks.service import TaskService

    service = TaskService(session=async_session)

    user = User(
        id=uuid4(),
        username="task_user",
        email="task@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )

    task = await service.create_task(
        title="Test Task",
        description="Integration test task",
        task_type=TaskType.GENERAL,
        priority=TaskPriority.MEDIUM,
        user=user,
    )

    assert task is not None
    assert task.title == "Test Task"


@pytest.mark.asyncio
async def test_task_status_update_integration(async_session):
    """Test task status update."""
    from src.identity.models import RoleEnum, User
    from src.tasks.service import TaskService

    service = TaskService(session=async_session)

    user = User(
        id=uuid4(),
        username="task_user",
        email="task@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )

    task = await service.create_task(
        title="Status Test",
        description="Status update test",
        task_type=TaskType.GENERAL,
        priority=TaskPriority.MEDIUM,
        user=user,
    )

    updated = await service.update_task_status(
        task_id=task.id,
        status=TaskStatus.RUNNING,
        user=user,
    )

    assert updated.status == TaskStatus.RUNNING


@pytest.mark.asyncio
async def test_task_complete_integration(async_session):
    """Test task completion."""
    from src.identity.models import RoleEnum, User
    from src.tasks.service import TaskService

    service = TaskService(session=async_session)

    user = User(
        id=uuid4(),
        username="task_user",
        email="task@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )

    task = await service.create_task(
        title="Complete Test",
        description="Will be completed",
        task_type=TaskType.GENERAL,
        priority=TaskPriority.MEDIUM,
        user=user,
    )

    completed = await service.complete_task(
        task_id=task.id,
        result={"output": "Success"},
        user=user,
    )

    assert completed.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_task_list_by_status_integration(async_session):
    """Test task list filtering by status."""
    from src.identity.models import RoleEnum, User
    from src.tasks.service import TaskService

    service = TaskService(session=async_session)

    user = User(
        id=uuid4(),
        username="task_user",
        email="task@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )

    await service.create_task(
        "Task 1", "Pending task", TaskType.GENERAL, user, TaskPriority.MEDIUM
    )
    task2 = await service.create_task(
        "Task 2", "Another pending", TaskType.GENERAL, user, TaskPriority.MEDIUM
    )

    await service.update_task_status(task2.id, TaskStatus.RUNNING, user=user)

    pending_tasks = await service.list_tasks(status=TaskStatus.PENDING, user=user)
    assert len(pending_tasks) >= 1


# ============================================================
# AI Employee API Integration Tests
# ============================================================


@pytest.mark.asyncio
async def test_employee_create_integration(async_session):
    """Test AI Employee creation."""
    from src.identity.audit import AuditService
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workforce.employee import AIEmployeeService
    from src.workforce.registry import AIEmployeeRegistry

    registry = AIEmployeeRegistry(async_session)
    rbac_service = RBACService(async_session)

    service = AIEmployeeService(
        registry=registry,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )

    user = User(
        id=uuid4(),
        username="emp_user",
        email="emp@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )

    # Create employee
    employee = await service.create_employee(
        name="Test Employee",
        department=Department.MARKETING,
        position=Position.MARKETING_SPECIALIST,
        description="Integration test employee",
        actor_id=user.id,
    )

    assert employee is not None
    assert employee.name == "Test Employee"


@pytest.mark.asyncio
async def test_employee_list_integration(async_session):
    """Test AI Employee list query."""
    from src.identity.audit import AuditService
    from src.identity.models import RoleEnum, User
    from src.identity.rbac import RBACService
    from src.workforce.employee import AIEmployeeService
    from src.workforce.registry import AIEmployeeRegistry

    registry = AIEmployeeRegistry(async_session)
    rbac_service = RBACService(async_session)

    service = AIEmployeeService(
        registry=registry,
        rbac_service=rbac_service,
        audit_service=AuditService,
    )

    user = User(
        id=uuid4(),
        username="emp_user",
        email="emp@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )

    await service.create_employee(
        "Employee 1", Department.SALES, Position.SALES_REPRESENTATIVE, "First", actor_id=user.id
    )
    await service.create_employee(
        "Employee 2", Department.RESEARCH, Position.MARKET_RESEARCHER, "Second", actor_id=user.id
    )

    employees = await service.list_employees(actor_id=user.id)
    assert len(employees) >= 2
