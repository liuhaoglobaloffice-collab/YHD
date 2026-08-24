"""
Phase 2E - WorkflowRepository Tests
Tests CRUD operations, model conversion, and database integration
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.database.repositories.workflow import WorkflowRepository
from src.workflow.models import (
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
)


@pytest.mark.asyncio
async def test_workflow_repo_create(workflow_repo: WorkflowRepository):
    """Test: Can create workflow in database"""
    # Create workflow
    workflow_id = uuid4()
    workflow = Workflow(
        workflow_id=workflow_id,
        name="Test Workflow",
        description="Test workflow description",
        status=WorkflowStatus.ACTIVE,
        steps=[],
        created_by=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        required_permissions=[],
        tags=["test"],
        metadata={},
    )

    # Save to database via repository
    from src.database.repositories.converters import workflow_to_model

    model = workflow_to_model(workflow)
    created = await workflow_repo.create(model)

    assert created is not None
    assert created.id == str(workflow_id)
    assert created.name == "Test Workflow"
    assert created.enabled is True  # ACTIVE maps to enabled

    await workflow_repo.session.commit()


@pytest.mark.asyncio
async def test_workflow_repo_read(workflow_repo: WorkflowRepository):
    """Test: Can read workflow from database"""
    # Create workflow
    workflow_id = uuid4()
    workflow = Workflow(
        workflow_id=workflow_id,
        name="Read Test",
        description="Test reading",
        status=WorkflowStatus.ACTIVE,
        steps=[],
        created_by=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        required_permissions=[],
        tags=[],
        metadata={},
    )

    from src.database.repositories.converters import workflow_to_model

    model = workflow_to_model(workflow)
    await workflow_repo.create(model)
    await workflow_repo.session.commit()

    # Read back
    found = await workflow_repo.get_by_id(str(workflow_id))
    assert found is not None
    assert found.name == "Read Test"


@pytest.mark.asyncio
async def test_workflow_repo_update(workflow_repo: WorkflowRepository):
    """Test: Can update workflow in database"""
    # Create workflow
    workflow_id = uuid4()
    workflow = Workflow(
        workflow_id=workflow_id,
        name="Original Name",
        description="Original description",
        status=WorkflowStatus.ACTIVE,
        steps=[],
        created_by=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        required_permissions=[],
        tags=[],
        metadata={},
    )

    from src.database.repositories.converters import workflow_to_model

    model = workflow_to_model(workflow)
    created = await workflow_repo.create(model)
    await workflow_repo.session.commit()

    # Update
    created.name = "Updated Name"
    created.description = "Updated description"
    await workflow_repo.update(
        entity_id=str(created.id),
        values={"name": "Updated Name", "description": "Updated description"},
    )
    await workflow_repo.session.commit()

    # Read back to verify
    verified = await workflow_repo.get_by_id(str(created.id))
    assert verified is not None
    assert verified.name == "Updated Name"
    assert verified.description == "Updated description"

    # Verify persistence
    found = await workflow_repo.get_by_id(str(workflow_id))
    assert found.name == "Updated Name"


@pytest.mark.asyncio
async def test_workflow_repo_delete(workflow_repo: WorkflowRepository):
    """Test: Can delete workflow from database"""
    # Create workflow
    workflow_id = uuid4()
    workflow = Workflow(
        workflow_id=workflow_id,
        name="Delete Test",
        description="Will be deleted",
        status=WorkflowStatus.ACTIVE,
        steps=[],
        created_by=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        required_permissions=[],
        tags=[],
        metadata={},
    )

    from src.database.repositories.converters import workflow_to_model

    model = workflow_to_model(workflow)
    await workflow_repo.create(model)
    await workflow_repo.session.commit()

    # Delete
    await workflow_repo.delete(str(workflow_id))
    await workflow_repo.session.commit()

    # Verify deleted
    found = await workflow_repo.get_by_id(str(workflow_id))
    assert found is None


@pytest.mark.asyncio
async def test_workflow_repo_list_by_creator(workflow_repo: WorkflowRepository):
    """Test: Can list workflows by creator"""
    user_id = uuid4()

    # Create multiple workflows
    for i in range(3):
        workflow = Workflow(
            workflow_id=uuid4(),
            name=f"Workflow {i}",
            description=f"Workflow {i} description",
            status=WorkflowStatus.ACTIVE,
            steps=[],
            created_by=user_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            required_permissions=[],
            tags=[],
            metadata={},
        )
        from src.database.repositories.converters import workflow_to_model

        model = workflow_to_model(workflow)
        await workflow_repo.create(model)

    await workflow_repo.session.commit()

    # List by creator
    workflows = await workflow_repo.list_by_creator(user_id)
    assert len(workflows) == 3


@pytest.mark.asyncio
async def test_workflow_repo_list_enabled(workflow_repo: WorkflowRepository):
    """Test: Can list only enabled workflows"""
    user_id = uuid4()

    # Create active workflow
    active_workflow = Workflow(
        workflow_id=uuid4(),
        name="Active Workflow",
        description="Active",
        status=WorkflowStatus.ACTIVE,
        steps=[],
        created_by=user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        required_permissions=[],
        tags=[],
        metadata={},
    )

    # Create paused workflow
    paused_workflow = Workflow(
        workflow_id=uuid4(),
        name="Paused Workflow",
        description="Paused",
        status=WorkflowStatus.PAUSED,
        steps=[],
        created_by=user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        required_permissions=[],
        tags=[],
        metadata={},
    )

    from src.database.repositories.converters import workflow_to_model

    await workflow_repo.create(workflow_to_model(active_workflow))
    await workflow_repo.create(workflow_to_model(paused_workflow))
    await workflow_repo.session.commit()

    # List enabled only
    enabled = await workflow_repo.list_enabled()
    assert len(enabled) == 1
    assert enabled[0].name == "Active Workflow"


@pytest.mark.asyncio
async def test_workflow_with_steps(workflow_repo: WorkflowRepository):
    """Test: Can persist workflow with complex steps"""
    workflow_id = uuid4()

    # Create workflow with steps
    workflow = Workflow(
        workflow_id=workflow_id,
        name="Complex Workflow",
        description="Has steps",
        status=WorkflowStatus.ACTIVE,
        steps=[
            WorkflowStep(
                step_id="step1",
                step_type=WorkflowStepType.TASK,
                name="Step 1",
                description="First step",
                task_type="research",
                task_config={"query": "test"},
                steps=[],
                condition=None,
                true_steps=[],
                false_steps=[],
                loop_condition=None,
                max_iterations=10,
                timeout_seconds=300,
                max_retries=0,
                retry_delay_seconds=5,
                required_permissions=[],
            )
        ],
        created_by=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        required_permissions=[],
        tags=[],
        metadata={},
    )

    from src.database.repositories.converters import model_to_workflow, workflow_to_model

    model = workflow_to_model(workflow)
    await workflow_repo.create(model)
    await workflow_repo.session.commit()

    # Read back and convert
    found = await workflow_repo.get_by_id(str(workflow_id))
    assert found is not None

    # Convert to domain model
    domain_workflow = model_to_workflow(found)
    assert len(domain_workflow.steps) == 1
    assert domain_workflow.steps[0].step_id == "step1"
    assert domain_workflow.steps[0].step_type == WorkflowStepType.TASK
