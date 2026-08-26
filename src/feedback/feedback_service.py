from typing import Optional

from .feedback_model import Feedback
from .feedback_repository import FeedbackRepository


class FeedbackService:
    """Collect and persist feedback from AI tasks and workflow executions."""

    def __init__(self, repository: Optional[FeedbackRepository] = None):
        self.repo = repository or FeedbackRepository()

    def collect(
        self,
        task_id: str,
        workflow_id: str,
        agent_id: str,
        input_context: str,
        ai_output: str,
        human_label: str = "",
        score: float = 0.0,
    ) -> Feedback:
        feedback = Feedback(
            task_id=task_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            input_context=input_context,
            ai_output=ai_output,
            human_label=human_label,
            score=score,
        )
        return self.repo.add(feedback)

    def update_feedback(self, feedback_id: str, *, human_label: Optional[str] = None, score: Optional[float] = None) -> Feedback:
        updated = self.repo.update(feedback_id, human_label=human_label, score=score)
        if updated is None:
            raise KeyError(feedback_id)
        return updated

    def list_feedback(self):
        return self.repo.list()

    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        return self.repo.get(feedback_id)
