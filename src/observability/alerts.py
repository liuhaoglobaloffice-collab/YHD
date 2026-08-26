from typing import Any, Dict, List


class AlertManager:
    """A lightweight alert manager for threshold-based metric evaluation."""

    def __init__(self):
        self.error_threshold = 5
        self.resource_threshold = 90
        self.cost_threshold = 100

    def record_error_threshold(self, value: int) -> None:
        self.error_threshold = value

    def record_resource_threshold(self, value: int) -> None:
        self.resource_threshold = value

    def record_cost_threshold(self, value: int) -> None:
        self.cost_threshold = value

    def evaluate(self, sample: Dict[str, Any]) -> List[Dict[str, Any]]:
        alerts = []
        if sample.get("error_count", 0) >= self.error_threshold:
            alerts.append({"type": "error_threshold", "value": sample.get("error_count")})
        if sample.get("resource", 0) >= self.resource_threshold:
            alerts.append({"type": "resource_threshold", "value": sample.get("resource")})
        if sample.get("cost", 0) >= self.cost_threshold:
            alerts.append({"type": "cost_threshold", "value": sample.get("cost")})
        return alerts
