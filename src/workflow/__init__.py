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
    # WorkflowService and WorkflowExecutor not exported - import directly
]
