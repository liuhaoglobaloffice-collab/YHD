"""
Workflow models and data structures.

Workflow Patterns:
1. Sequential: Steps execute one after another
2. Parallel: Steps execute concurrently
3. Conditional: Branch based on conditions
4. Loop: Repeat steps based on criteria
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class WorkflowStatus(str, Enum):
    """Workflow definition status."""

    DRAFT = "DRAFT"  # Being designed
    ACTIVE = "ACTIVE"  # Ready for execution
    PAUSED = "PAUSED"  # Temporarily disabled
    ARCHIVED = "ARCHIVED"  # No longer used


class WorkflowStepType(str, Enum):
    """Step execution pattern."""

    SEQUENTIAL = "SEQUENTIAL"  # Execute steps in order
    PARALLEL = "PARALLEL"  # Execute steps concurrently
    CONDITIONAL = "CONDITIONAL"  # Branch based on condition
    LOOP = "LOOP"  # Repeat steps
    TASK = "TASK"  # Execute single task


class WorkflowExecutionStatus(str, Enum):
    """Workflow execution runtime status."""

    PENDING = "PENDING"  # Not started
    RUNNING = "RUNNING"  # In progress
    PAUSED = "PAUSED"  # Temporarily paused
    COMPLETED = "COMPLETED"  # Successfully finished
    FAILED = "FAILED"  # Failed with error
    CANCELLED = "CANCELLED"  # Manually cancelled


@dataclass
class WorkflowStep:
    """
    Single step in workflow definition.

    A step can be:
    - A task to execute
    - A container for sub-steps (sequential/parallel/conditional/loop)
    """

    step_id: str
    step_type: WorkflowStepType
    name: str
    description: str = ""

    # For TASK type: task configuration
    task_type: Optional[str] = None
    task_config: Dict[str, Any] = field(default_factory=dict)

    # For container types: sub-steps
    steps: List["WorkflowStep"] = field(default_factory=list)

    # For CONDITIONAL type: condition and branches
    condition: Optional[str] = None  # Python expression
    true_steps: List["WorkflowStep"] = field(default_factory=list)
    false_steps: List["WorkflowStep"] = field(default_factory=list)

    # For LOOP type: loop configuration
    loop_condition: Optional[str] = None  # Python expression
    max_iterations: int = 10

    # Step timeout
    timeout_seconds: Optional[int] = None

    # Retry configuration
    max_retries: int = 0
    retry_delay_seconds: int = 5

    # Required permissions
    required_permissions: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate step configuration."""
        if not self.name or not self.name.strip():
            raise ValueError("Step name is required")

        if self.step_type == WorkflowStepType.TASK and not self.task_type:
            raise ValueError("TASK step requires task_type")

        if self.step_type == WorkflowStepType.CONDITIONAL and not self.condition:
            raise ValueError("CONDITIONAL step requires condition")

        if self.step_type == WorkflowStepType.LOOP and not self.loop_condition:
            raise ValueError("LOOP step requires loop_condition")


@dataclass
class WorkflowExecution:
    """
    Runtime state of workflow execution.
    """

    execution_id: UUID = field(default_factory=uuid4)
    workflow_id: UUID = field(default=None)
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.PENDING

    # Execution context
    started_by: UUID = field(default=None)  # User ID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Runtime state
    current_step: Optional[str] = None  # Current step_id
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)

    # Execution variables (shared context between steps)
    variables: Dict[str, Any] = field(default_factory=dict)

    # Step results
    step_results: Dict[str, Any] = field(default_factory=dict)

    # Error information
    error: Optional[str] = None
    error_step: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        """Check if execution is in terminal state."""
        return self.status in [
            WorkflowExecutionStatus.COMPLETED,
            WorkflowExecutionStatus.FAILED,
            WorkflowExecutionStatus.CANCELLED,
        ]

    def mark_step_completed(self, step_id: str, result: Any = None):
        """Mark step as completed."""
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)
        if result is not None:
            self.step_results[step_id] = result

    def mark_step_failed(self, step_id: str, error: str):
        """Mark step as failed."""
        if step_id not in self.failed_steps:
            self.failed_steps.append(step_id)
        self.error_step = step_id
        self.error = error


@dataclass
class Workflow:
    """
    Workflow definition - a reusable process template.
    """

    workflow_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    status: WorkflowStatus = WorkflowStatus.DRAFT

    # Workflow steps
    steps: List[WorkflowStep] = field(default_factory=list)

    # Ownership
    created_by: Optional[int] = None  # User ID
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Access control
    required_permissions: List[str] = field(default_factory=list)

    # Workflow configuration
    max_concurrent_executions: int = 1
    default_timeout_seconds: Optional[int] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        """
        Validate workflow definition.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.name:
            errors.append("Workflow name is required")

        if not self.steps:
            errors.append("Workflow must have at least one step")

        # Check for duplicate step IDs
        step_ids = self._collect_step_ids(self.steps)
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs found")

        # Validate each step
        for step in self.steps:
            try:
                step.__post_init__()
            except ValueError as e:
                errors.append(f"Step {step.step_id}: {str(e)}")

        return errors

    def _collect_step_ids(self, steps: List[WorkflowStep]) -> List[str]:
        """Recursively collect all step IDs."""
        step_ids = []
        for step in steps:
            step_ids.append(step.step_id)
            if step.steps:
                step_ids.extend(self._collect_step_ids(step.steps))
            if step.true_steps:
                step_ids.extend(self._collect_step_ids(step.true_steps))
            if step.false_steps:
                step_ids.extend(self._collect_step_ids(step.false_steps))
        return step_ids

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Find step by ID."""
        return self._find_step(step_id, self.steps)

    def _find_step(self, step_id: str, steps: List[WorkflowStep]) -> Optional[WorkflowStep]:
        """Recursively find step by ID."""
        for step in steps:
            if step.step_id == step_id:
                return step

            # Search in sub-steps
            if step.steps:
                found = self._find_step(step_id, step.steps)
                if found:
                    return found

            # Search in conditional branches
            if step.true_steps:
                found = self._find_step(step_id, step.true_steps)
                if found:
                    return found

            if step.false_steps:
                found = self._find_step(step_id, step.false_steps)
                if found:
                    return found

        return None
