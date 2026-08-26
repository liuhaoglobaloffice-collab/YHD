from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4


@dataclass
class Feedback:
    """A lightweight feedback record collected from task, workflow, or agent execution."""

    feedback_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    workflow_id: str = ""
    agent_id: str = ""
    input_context: str = ""
    ai_output: str = ""
    human_label: str = ""
    score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "feedback_id": self.feedback_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "agent_id": self.agent_id,
            "input_context": self.input_context,
            "ai_output": self.ai_output,
            "human_label": self.human_label,
            "score": self.score,
            "created_at": self.created_at.isoformat(),
        }
