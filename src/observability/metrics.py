from dataclasses import dataclass, field
from typing import Dict, List, Optional


class MetricsCollector:
    """A tiny metrics collector for API latency, task time, workflow success, errors, and LLM usage."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}

    def record_metric(self, name: str, value: float) -> None:
        self.metrics.setdefault(name, []).append(value)

    def summary(self) -> Dict[str, float]:
        return {name: sum(values) / len(values) if values else 0.0 for name, values in self.metrics.items()}
