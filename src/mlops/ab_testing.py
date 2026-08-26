from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


@dataclass
class ResultMetrics:
    accuracy: float = 0.0
    task_success_rate: float = 0.0
    human_score: float = 0.0
    execution_quality: float = 0.0


class ABTest:
    """A tiny A/B testing framework with user assignment and metric collection."""

    def __init__(
        self,
        test_id: str,
        model_a: str,
        model_b: str,
        traffic_split: Optional[Dict[str, int]] = None,
        user_group: str = "default",
    ):
        self.test_id = test_id
        self.model_a = model_a
        self.model_b = model_b
        self.traffic_split = traffic_split or {"A": 50, "B": 50}
        self.user_group = user_group
        self.metrics: Dict[str, ResultMetrics] = {}
        self.assignments: Dict[str, str] = {}

    def assign(self, user_id: str) -> str:
        bucket = "A" if abs(hash(user_id)) % 100 < self.traffic_split.get("A", 50) else "B"
        self.assignments[user_id] = bucket
        return bucket

    def record_results(self, bucket: str, metrics: ResultMetrics) -> ResultMetrics:
        self.metrics[bucket] = metrics
        return metrics

    def compare_metrics(self) -> Dict[str, float]:
        a = self.metrics.get("A", ResultMetrics())
        b = self.metrics.get("B", ResultMetrics())
        return {
            "accuracy": (a.accuracy + b.accuracy) / 2,
            "task_success_rate": (a.task_success_rate + b.task_success_rate) / 2,
            "human_score": (a.human_score + b.human_score) / 2,
            "execution_quality": (a.execution_quality + b.execution_quality) / 2,
        }
