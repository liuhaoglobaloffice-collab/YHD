"""
Tests for WorkflowService - CRUD operations with RBAC and audit
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.identity.audit import AuditService
from src.identity.models import RoleEnum, User
from src.identity.rbac import RBACService
from src.workflow.models import WorkflowStatus
from src.workflow.service import WorkflowService


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
    audit.log = AsyncMock()
    return audit


@pytest.fixture
def mock_policy():
    """Mock policy engine"""
    policy = Mock()
    return policy


@pytest.fixture
def admin_user():
    """Create admin user"""
    user = User(
        id=1,
        username="admin",
        email="admin@test.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    return user


@pytest.fixture
def workflow_service(async_session, mock_rbac, mock_audit):
    """Create workflow service with mocks"""
    return WorkflowService(
        session=async_session,
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    )


async def test_create_workflow_success(workflow_service, admin_user, mock_rbac, mock_audit):
    """Test creating workflow successfully"""
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Test Step",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test Description",
        steps=steps,
        user=admin_user,
        status=WorkflowStatus.DRAFT,
    )

    assert workflow.name == "Test Workflow"
    assert workflow.description == "Test Description"
    assert workflow.status == WorkflowStatus.DRAFT
    assert len(workflow.steps) == 1
    assert workflow.created_by == admin_user.id

    # Verify RBAC was checked
    mock_rbac.check_permission_by_id.assert_called()

    # Verify audit was logged
    assert mock_audit.log.call_count >= 1


async def test_create_workflow_permission_denied(workflow_service, admin_user, mock_rbac):
    """Test creating workflow without permission"""
    mock_rbac.check_permission_by_id = AsyncMock(return_value=False)

    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Test Step",
            "task_type": "test_task",
        }
    ]

    with pytest.raises(PermissionError):
        await workflow_service.create_workflow(
            name="Test Workflow",
            description="Test Description",
            steps=steps,
            user=admin_user,
        )


async def test_create_workflow_invalid_steps(workflow_service, admin_user):
    """Test creating workflow with invalid steps"""
    # Empty name should fail validation
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "",  # Empty name
            "task_type": "test_task",
        }
    ]

    with pytest.raises(ValueError):
        await workflow_service.create_workflow(
            name="Test Workflow",
            description="Test Description",
            steps=steps,
            user=admin_user,
        )


async def test_get_workflow_success(workflow_service, admin_user, mock_rbac):
    """Test getting workflow successfully"""
    # Create workflow first
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Test Step",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test Description",
        steps=steps,
        user=admin_user,
    )

    # Get workflow
    retrieved = await workflow_service.get_workflow(workflow.workflow_id, admin_user)

    assert retrieved is not None
    assert retrieved.workflow_id == workflow.workflow_id
    assert retrieved.name == "Test Workflow"


async def test_get_workflow_not_found(workflow_service, admin_user):
    """Test getting non-existent workflow"""
    workflow_id = uuid4()

    retrieved = await workflow_service.get_workflow(workflow_id, admin_user)

    assert retrieved is None


async def test_get_workflow_permission_denied(workflow_service, admin_user, mock_rbac):
    """Test getting workflow without permission"""
    mock_rbac.check_permission_by_id = AsyncMock(return_value=False)

    workflow_id = uuid4()

    with pytest.raises(PermissionError):
        await workflow_service.get_workflow(workflow_id, admin_user)


async def test_list_workflows(workflow_service, admin_user):
    """Test listing workflows"""
    # Create multiple workflows
    for i in range(3):
        steps = [
            {
                "step_id": f"step{i}",
                "step_type": "task",
                "name": f"Step {i}",
                "task_type": "test_task",
            }
        ]
        await workflow_service.create_workflow(
            name=f"Workflow {i}",
            description=f"Description {i}",
            steps=steps,
            user=admin_user,
        )

    # List all workflows
    workflows = await workflow_service.list_workflows(admin_user)

    assert len(workflows) == 3


async def test_list_workflows_with_filters(workflow_service, admin_user):
    """Test listing workflows with filters"""
    # Create workflows with different statuses
    for status in [WorkflowStatus.DRAFT, WorkflowStatus.ACTIVE]:
        steps = [
            {
                "step_id": "step1",
                "step_type": "task",
                "name": "Step 1",
                "task_type": "test_task",
            }
        ]
        await workflow_service.create_workflow(
            name=f"Workflow {status.value}",
            description="Description",
            steps=steps,
            user=admin_user,
            status=status,
        )

    # Filter by status
    draft_workflows = await workflow_service.list_workflows(
        admin_user,
        status=WorkflowStatus.DRAFT,
    )

    assert len(draft_workflows) >= 1
    assert all(w.status == WorkflowStatus.DRAFT for w in draft_workflows)


async def test_update_workflow_success(workflow_service, admin_user):
    """Test updating workflow successfully"""
    # Create workflow
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Step 1",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Original Name",
        description="Original Description",
        steps=steps,
        user=admin_user,
    )

    # Update workflow
    updated = await workflow_service.update_workflow(
        workflow.workflow_id,
        admin_user,
        name="Updated Name",
        description="Updated Description",
        status=WorkflowStatus.ACTIVE,
    )

    assert updated.name == "Updated Name"
    assert updated.description == "Updated Description"
    assert updated.status == WorkflowStatus.ACTIVE


async def test_update_workflow_not_found(workflow_service, admin_user):
    """Test updating non-existent workflow"""
    workflow_id = uuid4()

    with pytest.raises(ValueError):
        await workflow_service.update_workflow(
            workflow_id,
            admin_user,
            name="New Name",
        )


async def test_delete_workflow_success(workflow_service, admin_user):
    """Test deleting workflow successfully"""
    # Create workflow
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Step 1",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test Description",
        steps=steps,
        user=admin_user,
    )

    # Delete workflow
    result = await workflow_service.delete_workflow(workflow.workflow_id, admin_user)

    assert result is True

    # Verify deleted
    retrieved = await workflow_service.get_workflow(workflow.workflow_id, admin_user)
    assert retrieved is None


async def test_delete_workflow_not_found(workflow_service, admin_user):
    """Test deleting non-existent workflow"""
    workflow_id = uuid4()

    result = await workflow_service.delete_workflow(workflow_id, admin_user)

    assert result is False


async def test_validate_workflow(workflow_service, admin_user):
    """Test workflow validation"""
    # Create workflow
    steps = [
        {
            "step_id": "step1",
            "step_type": "task",
            "name": "Step 1",
            "task_type": "test_task",
        }
    ]

    workflow = await workflow_service.create_workflow(
        name="Test Workflow",
        description="Test Description",
        steps=steps,
        user=admin_user,
    )

    # Validate
    errors = await workflow_service.validate_workflow(workflow.workflow_id, admin_user)

    assert len(errors) == 0
