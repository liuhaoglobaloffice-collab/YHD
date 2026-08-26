"""
Workflow Engine - Orchestrates multi-step processes.

Architecture:
- Workflow: Process definition with steps
- WorkflowExecutor: Executes workflows (sequential, parallel, conditional, loop)
- WorkflowService: CRUD operations with RBAC + Audit

Key Principle: Workflow ≠ Agent
- Workflow orchestrates PROCESS
- Agent provides CAPABILITY
- Tasks bridge Workflow steps to Agent execution
"""

from .models import (
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
)
from .event_bus import EventBus
from .workflow import WorkflowEngine, WorkflowStep as WorkflowStepShim, WorkflowTask
from .state_machine import WorkflowStateMachine
from .templates import SupplierRiskWorkflowTemplate

# Service and Executor are not exported from __init__ to avoid circular imports
# Import them directly: from src.workflow.service import WorkflowService
# Import them directly: from src.workflow.executor import WorkflowExecutor

__all__ = [
    "Workflow",
    "WorkflowStatus",
    "WorkflowStep",
    "WorkflowStepType",
    "WorkflowExecution",
    "WorkflowExecutionStatus",
    "EventBus",
    "WorkflowEngine",
    "WorkflowStepShim",
    "WorkflowTask",
    "WorkflowStateMachine",
    "SupplierRiskWorkflowTemplate",
    # WorkflowService and WorkflowExecutor not exported - import directly
]
