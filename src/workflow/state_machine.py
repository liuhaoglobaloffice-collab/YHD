"""Small state machine for workflow execution."""

from typing import Any, Dict, Optional


class WorkflowStateMachine:
    """A tiny workflow state machine with a conservative transition model."""

    def __init__(self, workflow: Optional[Dict[str, Any]] = None):
        self.workflow = workflow or {"name": "workflow", "steps": [], "transitions": []}
        self.state = "CREATED"

    def start(self) -> str:
        self.state = "RUNNING"
        return self.state

    def pause(self) -> str:
        self.state = "WAITING"
        return self.state

    def complete(self) -> str:
        self.state = "COMPLETED"
        return self.state

    def fail(self) -> str:
        self.state = "FAILED"
        return self.state
