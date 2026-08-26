from typing import Dict, Iterable, List, Optional

from .feedback_model import Feedback


class FeedbackRepository:
    """In-memory repository for Phase 4 feedback collection."""

    def __init__(self):
        self._items: Dict[str, Feedback] = {}

    def add(self, feedback: Feedback) -> Feedback:
        self._items[feedback.feedback_id] = feedback
        return feedback

    def get(self, feedback_id: str) -> Optional[Feedback]:
        return self._items.get(feedback_id)

    def list(self) -> List[Feedback]:
        return list(self._items.values())

    def update(self, feedback_id: str, *, human_label: Optional[str] = None, score: Optional[float] = None) -> Optional[Feedback]:
        item = self._items.get(feedback_id)
        if not item:
            return None
        if human_label is not None:
            item.human_label = human_label
        if score is not None:
            item.score = score
        return item

    def by_task(self, task_id: str) -> List[Feedback]:
        return [item for item in self._items.values() if item.task_id == task_id]
