from typing import Any, Dict

from .experiment import Experiment


class TrainingJob:
    """A deterministic training job that simulates SFT-style experiment execution."""

    def __init__(self, experiment: Experiment):
        self.experiment = experiment

    def run(self) -> Dict[str, Any]:
        if not self.experiment.name:
            raise ValueError("experiment must have a name")
        return {
            "status": "completed",
            "experiment_name": self.experiment.name,
            "model_name": self.experiment.model_name,
            "dataset_version": self.experiment.dataset_version,
            "training_config": self.experiment.training_config or {"epochs": 1},
            "evaluation_metric": self.experiment.evaluation_metric,
            "metric_value": 0.90,
        }
