from uuid import uuid4

from src.feedback.feedback_service import FeedbackService
from src.feedback.feedback_repository import FeedbackRepository
from src.tasks.models import Task, TaskStatus


def test_feedback_auto_generated_for_completed_task():
    repo = FeedbackRepository()
    service = FeedbackService(repo)
    task = Task(id=uuid4(), title="Assessment task", status=TaskStatus.COMPLETED)

    feedback = service.collect(
        task_id=str(task.id),
        workflow_id=str(uuid4()),
        agent_id="agent-risk",
        input_context="Supplier risk context",
        ai_output="High risk supplier",
        human_label="Human correction",
        score=0.92,
    )

    assert feedback.feedback_id
    assert feedback.task_id == str(task.id)
    assert feedback.score == 0.92
    assert repo.get(feedback.feedback_id)


def test_feedback_human_score_can_be_written_and_queried():
    repo = FeedbackRepository()
    service = FeedbackService(repo)

    feedback = service.collect(
        task_id=str(uuid4()),
        workflow_id=str(uuid4()),
        agent_id="agent-risk",
        input_context="Context",
        ai_output="Answer",
        human_label="",
        score=0.50,
    )

    updated = service.update_feedback(feedback.feedback_id, human_label="accepted", score=0.95)
    assert updated.human_label == "accepted"
    assert updated.score == 0.95

    listed = service.list_feedback()
    assert any(item.feedback_id == feedback.feedback_id for item in listed)
