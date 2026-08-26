from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class Experiment:
    """A lightweight experiment metadata record for an SFT-style simulation."""

    name: str
    model_name: str = "mock-model"
    dataset_version: str = "v1"
    training_config: Dict[str, Any] = field(default_factory=dict)
    evaluation_metric: str = "accuracy"
    experiment_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model_name": self.model_name,
            "dataset_version": self.dataset_version,
            "training_config": self.training_config,
            "evaluation_metric": self.evaluation_metric,
            "experiment_result": self.experiment_result,
        }
