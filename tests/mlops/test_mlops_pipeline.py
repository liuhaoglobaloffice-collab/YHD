from uuid import uuid4

from src.datasets.dataset_builder import DatasetBuilder
from src.datasets.dataset_service import DatasetService
from src.feedback.feedback_repository import FeedbackRepository
from src.feedback.feedback_service import FeedbackService
from src.mlops.experiment import Experiment
from src.mlops.trainer import TrainingJob
from src.mlops.evaluator import Evaluator
from src.mlops.model_registry import ModelRegistry


def test_dataset_builder_creates_training_sample_from_feedback():
    repo = FeedbackRepository()
    feedback_service = FeedbackService(repo)
    feedback = feedback_service.collect(
        task_id=str(uuid4()),
        workflow_id=str(uuid4()),
        agent_id="agent-risk",
        input_context="User asks about supplier map",
        ai_output="Supplier is high risk",
        human_label="Supplier is high risk and needs review",
        score=0.92,
    )

    dataset_service = DatasetService()
    builder = DatasetBuilder(dataset_service)
    dataset = builder.build_from_feedback(feedback)

    assert dataset.name
    assert dataset.samples[0].input == "User asks about supplier map"
    assert dataset.samples[0].context == "User asks about supplier map"
    assert dataset.samples[0].output == "Supplier is high risk"
    assert dataset.samples[0].label == "Supplier is high risk and needs review"
    assert dataset.samples[0].quality_score == 0.92


def test_training_experiment_and_model_registry_flow():
    experiment = Experiment(name="sft_safety_experiment", model_name="mock-model", dataset_version="v1")
    job = TrainingJob(experiment)
    result = job.run()
    evaluator = Evaluator()
    assessment = evaluator.evaluate(result)

    registry = ModelRegistry()
    version = registry.register("v2", assessment)

    assert result["status"] == "completed"
    assert assessment["accuracy"] >= 0
    assert version.model_version == "v2"
