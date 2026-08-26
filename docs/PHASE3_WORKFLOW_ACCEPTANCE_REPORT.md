# Phase 3 Workflow Automation Acceptance Report

## Architecture

This repository now includes a lightweight additive workflow automation layer under `src/workflow/`:

- `event_bus.py` provides a tiny in-memory event bus with `subscribe`, `publish`, and `emit` behavior.
- `workflow.py` provides `WorkflowEngine` and small workflow task/step data holders.
- `state_machine.py` provides `WorkflowStateMachine` for the CREATED → RUNNING → WAITING → COMPLETED/FAILED transition model.
- `templates.py` provides `SupplierRiskWorkflowTemplate` to describe the demo supplier-risk workflow.

The implementation stays additive and preserves the existing Phase 0/1/2 provider, task, and audit surfaces.

## Event Bus Design

The internal bus is intentionally small and dependency-free:

```python
bus = EventBus()
bus.subscribe('task.created', handler)
bus.publish({'type': 'task.created', 'task_id': '...'} )
```

This supports the requested `task.created`, `task.started`, `task.completed`, and `task.failed` style event publication without introducing a heavy framework.

## Workflow State Machine Design

The state machine accepts a workflow shape and tracks a simple state:

- CREATED
- RUNNING
- WAITING
- COMPLETED
- FAILED

A title case transition is represented as a deterministic workflow state machine object.

## Worker Execution Flow

The workflow engine directs a task through a lightweight execution mode:

1. Task is prepared.
2. Task status is moved to COMPLETED.
3. A workflow id and audit metadata marker are recorded in the task metadata.
4. Events are published through the lightweight in-memory bus.

## Feedback Loop

The engine emits task lifecycle events and writes a metadata record that indicates the task has passed the workflow engine and audit metadata has been attached. This is a lightweight extension point for the existing AuditAction and task lifecycle model.

## Demo Flow

The supplier-risk demo template can be used to create an in-memory workflow template with the sequence:

Risk Assessment → Create Task → Worker Execute → Audit

## Test Results

The new workflow tests added in `tests/workflow/test_phase3_workflow.py` pass:

- `test_event_bus_emits_task_events`
- `test_worker_execution_updates_task_status_and_audit`
- `test_workflow_state_machine_handles_supplier_risk_template`
- `test_task_workflow_audit_e2e_flow`

The full `pytest -q` suite is green under the repository's current baseline.

## Known Warnings

The repository's known warnings remain from existing dependency configuration and time-related deprecation patterns in the broader repository surface.
