import os

os.environ.setdefault("SECRET_KEY", "1234567890abcdef1234567890abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "1234567890abcdef1234567890abcdef")

from src.workflow.models import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType


def test_workflow_definition_smoke():
    workflow = Workflow(
        name="Release Workflow",
        description="Smoke test workflow",
        status=WorkflowStatus.ACTIVE,
        steps=[
            WorkflowStep(
                step_id="step_1",
                step_type=WorkflowStepType.TASK,
                name="Initial task",
                task_type="supplier_check",
                task_config={"mode": "smoke"},
            )
        ],
    )

    errors = workflow.validate()
    assert errors == [], errors
    assert workflow.steps[0].name == "Initial task"
    assert workflow.status == WorkflowStatus.ACTIVE
