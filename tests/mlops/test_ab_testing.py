from src.mlops.ab_testing import ABTest, ResultMetrics
from src.mlops.model_registry import ModelRegistry, ModelVersion, ModelStatus


def test_model_registry_version_lifecycle_and_ab_testing_flow():
    registry = ModelRegistry()
    model = registry.register(
        model_name="risk_classifier",
        model_version="v2",
        experiment_id="exp-42",
        dataset_version="v1",
        metrics={"accuracy": 0.88},
        status=ModelStatus.CREATED,
    )

    assert model.model_name == "risk_classifier"
    assert model.model_version == "v2"
    assert registry.get("risk_classifier", "v2")

    registry.update_status("risk_classifier", "v2", ModelStatus.TESTING)
    model = registry.get("risk_classifier", "v2")
    assert model.status == ModelStatus.TESTING

    ab = ABTest(
        test_id="ab-risk-01",
        model_a="v1",
        model_b="v2",
        traffic_split={"A": 50, "B": 50},
        user_group="risk-reviewers",
    )
    assignment = ab.assign("reviewer-001")
    assert assignment in {"A", "B"}

    metrics = ResultMetrics(accuracy=0.91, task_success_rate=0.91, human_score=0.90, execution_quality=0.89)
    ab.record_results(assignment, metrics)

    comparison = ab.compare_metrics()
    assert comparison["accuracy"] >= 0
