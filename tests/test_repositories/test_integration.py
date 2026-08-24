"""
Phase 2E - Quick Repository Integration Tests
Simplified tests to verify basic CRUD operations work
"""

from uuid import uuid4

import pytest

from src.database.repositories.task import TaskRepository
from src.database.repositories.workflow import WorkflowRepository
from src.tasks.models import Task, TaskPriority, TaskStatus, TaskType
from src.workflow.models import Workflow, WorkflowStatus


@pytest.mark.asyncio
async def test_workflow_basic_crud(workflow_repo: WorkflowRepository):
    """Test: Basic workflow CRUD via repository"""
    workflow_id = uuid4()

    # Create
    from src.database.repositories.converters import workflow_to_model

    workflow = Workflow(
        workflow_id=workflow_id,
        name="Test Workflow",
        description="Test",
        status=WorkflowStatus.ACTIVE,
        steps=[],
        created_by=uuid4(),
    )
    model = workflow_to_model(workflow)
    created = await workflow_repo.create(model)
    await workflow_repo.session.commit()

    assert created.id == str(workflow_id)

    # Read
    found = await workflow_repo.get_by_id(str(workflow_id))
    assert found is not None
    assert found.name == "Test Workflow"

    # Delete
    await workflow_repo.delete(str(workflow_id))
    await workflow_repo.session.commit()

    deleted = await workflow_repo.get_by_id(str(workflow_id))
    assert deleted is None


@pytest.mark.asyncio
async def test_task_basic_crud(task_repo: TaskRepository):
    """Test: Basic task CRUD via repository"""
    task_id = uuid4()
    creator_id = uuid4()

    from src.database.repositories.converters import task_to_model

    task = Task(
        id=task_id,
        title="Test Task",
        description="Test task description",
        task_type=TaskType.RESEARCH,
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
        creator_id=creator_id,
    )

    model = task_to_model(task)
    created = await task_repo.create(model)
    await task_repo.session.commit()

    assert created.id == str(task_id)
    assert created.title == "Test Task"

    # Read
    found = await task_repo.get_by_id(str(task_id))
    assert found is not None
    assert found.status == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_converters_roundtrip():
    """Test: Converters can round-trip domain to database models"""
    from src.database.repositories.converters import model_to_workflow, workflow_to_model

    original = Workflow(
        workflow_id=uuid4(),
        name="Roundtrip Test",
        description="Test conversion",
        status=WorkflowStatus.ACTIVE,
        steps=[],
        created_by=uuid4(),
    )

    # Domain to Database
    db_model = workflow_to_model(original)
    assert db_model.name == "Roundtrip Test"

    # Database to Domain
    domain_model = model_to_workflow(db_model)
    assert domain_model.name == "Roundtrip Test"
    assert domain_model.status == WorkflowStatus.ACTIVE
