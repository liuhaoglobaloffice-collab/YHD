from typing import Any, Dict, List

from .feedback_service import FeedbackService


class FeedbackAPI:
    """Minimal API facade for the feedback collection pipeline."""

    def __init__(self, service: FeedbackService):
        self.service = service

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        feedback = self.service.collect(
            task_id=payload.get("task_id", ""),
            workflow_id=payload.get("workflow_id", ""),
            agent_id=payload.get("agent_id", ""),
            input_context=payload.get("input_context", ""),
            ai_output=payload.get("ai_output", ""),
            human_label=payload.get("human_label", ""),
            score=float(payload.get("score", 0.0)),
        )
        return feedback.to_dict()

    def list(self) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self.service.list_feedback()]
