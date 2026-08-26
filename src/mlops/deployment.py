from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeploymentMode(str, Enum):
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ROLLBACK = "ROLLBACK"


class ModelDeployment:
    """A minimal model deployment object with gray release and rollback support."""

    def __init__(self, model_name: str, model_version: str):
        self.model_name = model_name
        self.model_version = model_version
        self.current_traffic = 0
        self.status = DeploymentMode.STAGING.value

    def deploy(self, traffic_percent: int = 10) -> "ModelDeployment":
        self.current_traffic = traffic_percent
        self.status = DeploymentMode.STAGING.value
        return self

    def promote(self, traffic_percent: int = 100) -> "ModelDeployment":
        self.current_traffic = traffic_percent
        self.status = DeploymentMode.PRODUCTION.value
        return self

    def rollback(self) -> "ModelDeployment":
        self.current_traffic = 0
        self.status = DeploymentMode.ROLLBACK.value
        return self
