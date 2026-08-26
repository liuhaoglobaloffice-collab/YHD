from typing import Optional

from src.feedback.feedback_model import Feedback
from .dataset_model import Dataset, TrainingSample
from .dataset_service import DatasetService


class DatasetBuilder:
    """Convert a feedback record into a training sample dataset."""

    def __init__(self, dataset_service: Optional[DatasetService] = None):
        self.dataset_service = dataset_service or DatasetService()

    def build_from_feedback(self, feedback: Feedback, name: str = "feedback_dataset") -> Dataset:
        dataset = self.dataset_service.create_dataset(name, version="v1")
        sample = TrainingSample(
            input=feedback.input_context,
            context=feedback.input_context,
            output=feedback.ai_output,
            label=feedback.human_label or feedback.ai_output,
            quality_score=feedback.score,
        )
        self.dataset_service.add_sample(dataset, sample)
        return dataset
