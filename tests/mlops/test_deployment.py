from src.mlops.deployment import ModelDeployment, DeploymentMode
from src.mlops.model_registry import ModelRegistry, ModelStatus


def test_gray_release_and_rollback_flow():
    registry = ModelRegistry()
    registry.register(
        model_name="risk_classifier",
        model_version="v2",
        experiment_id="exp-42",
        dataset_version="v1",
        metrics={"accuracy": 0.90},
        status=ModelStatus.STAGING,
    )

    deployment = ModelDeployment(model_name="risk_classifier", model_version="v2")
    deployment.deploy(traffic_percent=10)
    assert deployment.current_traffic == 10
    assert deployment.status == DeploymentMode.STAGING.value

    deployment.promote(traffic_percent=100)
    assert deployment.current_traffic == 100
    assert deployment.status == DeploymentMode.PRODUCTION.value

    deployment.rollback()
    assert deployment.status == DeploymentMode.ROLLBACK.value
