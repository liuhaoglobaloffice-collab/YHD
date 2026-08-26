from typing import Any, Dict


class Evaluator:
    """Collect a deterministic evaluation result from a training outcome."""

    def evaluate(self, training_result: Dict[str, Any]) -> Dict[str, Any]:
        score = float(training_result.get("metric_value", 0.0))
        return {
            "accuracy": score,
            "task_success_rate": score,
            "human_score": score,
            "execution_quality": score,
            "metric_name": "accuracy",
            "status": "evaluated",
        }
