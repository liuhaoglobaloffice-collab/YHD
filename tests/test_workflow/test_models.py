"""
Tests for workflow models and validation
"""

from datetime import UTC, datetime
from uuid import uuid4

from src.workflow.models import (
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
)


def test_workflow_step_creation():
    """Test creating workflow step"""
    step = WorkflowStep(
        step_id="step1",
        step_type=WorkflowStepType.TASK,
        name="Test Step",
        description="Test Description",
        task_type="test_task",
        task_config={"param": "value"},
    )

    assert step.step_id == "step1"
    assert step.step_type == WorkflowStepType.TASK
    assert step.name == "Test Step"
    assert step.task_type == "test_task"
    assert step.task_config == {"param": "value"}


def test_workflow_step_sequential():
    """Test sequential workflow step"""
    steps = [
        WorkflowStep(
            step_id="sub1",
            step_type=WorkflowStepType.TASK,
            name="Sub Step 1",
            task_type="task1",
        ),
        WorkflowStep(
            step_id="sub2",
            step_type=WorkflowStepType.TASK,
            name="Sub Step 2",
            task_type="task2",
        ),
    ]

    sequential_step = WorkflowStep(
        step_id="seq1",
        step_type=WorkflowStepType.SEQUENTIAL,
        name="Sequential Steps",
        steps=steps,
    )

    assert sequential_step.step_type == WorkflowStepType.SEQUENTIAL
    assert len(sequential_step.steps) == 2


def test_workflow_step_parallel():
    """Test parallel workflow step"""
    steps = [
        WorkflowStep(
            step_id="par1",
            step_type=WorkflowStepType.TASK,
            name="Parallel Task 1",
            task_type="task1",
        ),
        WorkflowStep(
            step_id="par2",
            step_type=WorkflowStepType.TASK,
            name="Parallel Task 2",
            task_type="task2",
        ),
    ]

    parallel_step = WorkflowStep(
        step_id="parallel1",
        step_type=WorkflowStepType.PARALLEL,
        name="Parallel Steps",
        steps=steps,
    )

    assert parallel_step.step_type == WorkflowStepType.PARALLEL
    assert len(parallel_step.steps) == 2


def test_workflow_step_conditional():
    """Test conditional workflow step"""
    true_steps = [
        WorkflowStep(
            step_id="true1",
            step_type=WorkflowStepType.TASK,
            name="True Branch",
            task_type="task_true",
        )
    ]

    false_steps = [
        WorkflowStep(
            step_id="false1",
            step_type=WorkflowStepType.TASK,
            name="False Branch",
            task_type="task_false",
        )
    ]

    conditional_step = WorkflowStep(
        step_id="cond1",
        step_type=WorkflowStepType.CONDITIONAL,
        name="Conditional Step",
        condition="variables.status == 'active'",
        true_steps=true_steps,
        false_steps=false_steps,
    )

    assert conditional_step.step_type == WorkflowStepType.CONDITIONAL
    assert conditional_step.condition == "variables.status == 'active'"
    assert len(conditional_step.true_steps) == 1
    assert len(conditional_step.false_steps) == 1


def test_workflow_step_loop():
    """Test loop workflow step"""
    loop_steps = [
        WorkflowStep(
            step_id="loop_body",
            step_type=WorkflowStepType.TASK,
            name="Loop Body",
            task_type="task_loop",
        )
    ]

    loop_step = WorkflowStep(
        step_id="loop1",
        step_type=WorkflowStepType.LOOP,
        name="Loop Step",
        steps=loop_steps,
        loop_condition="variables.counter < 5",
        max_iterations=10,
    )

    assert loop_step.step_type == WorkflowStepType.LOOP
    assert loop_step.loop_condition == "variables.counter < 5"
    assert loop_step.max_iterations == 10


def test_workflow_creation():
    """Test creating workflow"""
    steps = [
        WorkflowStep(
            step_id="step1",
            step_type=WorkflowStepType.TASK,
            name="Step 1",
            task_type="test_task",
        )
    ]

    workflow = Workflow(
        name="Test Workflow",
        description="Test Description",
        status=WorkflowStatus.DRAFT,
        steps=steps,
        created_by=1,
    )

    assert workflow.name == "Test Workflow"
    assert workflow.status == WorkflowStatus.DRAFT
    assert len(workflow.steps) == 1
    assert workflow.created_by == 1


def test_workflow_validation_empty_name():
    """Test workflow validation - empty name"""
    workflow = Workflow(
        name="",
        description="Test",
        status=WorkflowStatus.DRAFT,
        steps=[],
        created_by=1,
    )

    errors = workflow.validate()
    assert any("name" in err.lower() for err in errors)


def test_workflow_validation_no_steps():
    """Test workflow validation - no steps"""
    workflow = Workflow(
        name="Test",
        description="Test",
        status=WorkflowStatus.DRAFT,
        steps=[],
        created_by=1,
    )

    errors = workflow.validate()
    assert any("step" in err.lower() for err in errors)


def test_workflow_validation_valid():
    """Test workflow validation - valid workflow"""
    steps = [
        WorkflowStep(
            step_id="step1",
            step_type=WorkflowStepType.TASK,
            name="Step 1",
            task_type="test_task",
        )
    ]

    workflow = Workflow(
        name="Test Workflow",
        description="Test Description",
        status=WorkflowStatus.DRAFT,
        steps=steps,
        created_by=1,
    )

    errors = workflow.validate()
    assert len(errors) == 0


def test_workflow_execution_creation():
    """Test creating workflow execution"""
    workflow_id = uuid4()
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        started_by=1,
        variables={"key": "value"},
    )

    assert execution.workflow_id == workflow_id
    assert execution.started_by == 1
    assert execution.status == WorkflowExecutionStatus.PENDING
    assert execution.variables == {"key": "value"}


def test_workflow_execution_complete():
    """Test completing workflow execution"""
    workflow_id = uuid4()
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        started_by=1,
    )

    execution.status = WorkflowExecutionStatus.RUNNING
    execution.start_time = datetime.now(UTC)

    execution.status = WorkflowExecutionStatus.COMPLETED
    execution.end_time = datetime.now(UTC)
    execution.result = {"output": "success"}

    assert execution.status == WorkflowExecutionStatus.COMPLETED
    assert execution.result == {"output": "success"}
    assert execution.end_time is not None


def test_workflow_execution_failed():
    """Test failed workflow execution"""
    workflow_id = uuid4()
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        started_by=1,
    )

    execution.status = WorkflowExecutionStatus.RUNNING
    execution.start_time = datetime.now(UTC)

    execution.status = WorkflowExecutionStatus.FAILED
    execution.end_time = datetime.now(UTC)
    execution.error = "Test error"

    assert execution.status == WorkflowExecutionStatus.FAILED
    assert execution.error == "Test error"
