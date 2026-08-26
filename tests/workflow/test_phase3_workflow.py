from uuid import uuid4

from src.identity.audit import AuditAction
from src.tasks.models import Task, TaskPriority, TaskStatus, TaskType
from src.workflow.event_bus import EventBus
from src.workflow.templates import SupplierRiskWorkflowTemplate
from src.workflow.workflow import WorkflowEngine
from src.workflow.state_machine import WorkflowStateMachine


def test_event_bus_emits_task_events():
    bus = EventBus()
    received = []

    def on_created(event):
        received.append(event["type"])

    bus.subscribe("task.created", on_created)
    bus.publish({"type": "task.created", "task_id": str(uuid4())})

    assert received == ["task.created"]


def test_worker_execution_updates_task_status_and_audit():
    workflow = WorkflowEngine()
    task = Task(
        id=uuid4(),
        title="Supplier risk assessment",
        description="Run a high risk supplier assessment",
        task_type=TaskType.RESEARCH,
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
    )

    result = workflow.execute_task(task, worker="risk_worker")

    assert result.success is True
    assert task.status == TaskStatus.COMPLETED
    assert task.metadata.get("workflow_id")
    assert task.metadata.get("audit_written") is True


def test_workflow_state_machine_handles_supplier_risk_template():
    template = SupplierRiskWorkflowTemplate()
    wf = template.build()
    machine = WorkflowStateMachine(wf)

    machine.start()
    assert machine.state == "RUNNING"

    machine.complete()
    assert machine.state == "COMPLETED"


def test_task_workflow_audit_e2e_flow():
    bus = EventBus()
    engine = WorkflowEngine(event_bus=bus)
    engine.subscribe("task.created", lambda event: None)

    task = Task(
        id=uuid4(),
        title="High risk supplier assessment",
        description="Supplier risk assessment",
        task_type=TaskType.RESEARCH,
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
    )

    workflow = SupplierRiskWorkflowTemplate().build()
    result = engine.execute_workflow(workflow, task)

    assert result["task_status"] == TaskStatus.COMPLETED.value
    assert result["audit_event"] == AuditAction.TASK_COMPLETED.value
    assert result["metadata"]["security_status"] == "passed"
