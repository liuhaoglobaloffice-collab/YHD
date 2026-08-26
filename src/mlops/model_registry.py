from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class ModelStatus(str, Enum):
    CREATED = "CREATED"
    TESTING = "TESTING"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


@dataclass
class RegisteredModel:
    model_name: str = ""
    model_version: str = ""
    experiment_id: str = ""
    dataset_version: str = ""
    metrics: Dict[str, float] = None
    status: ModelStatus = ModelStatus.CREATED

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}


@dataclass
class ModelVersion:
    model_name: str
    model_version: str
    experiment_id: str = ""
    dataset_version: str = ""
    metrics: Dict[str, float] = None
    status: ModelStatus = ModelStatus.CREATED

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}


class ModelRegistry:
    """Simple in-memory model registry for v1/v2 comparisons and rollout tracking."""

    def __init__(self):
        self.versions: Dict[str, ModelVersion] = {}
        self.models: Dict[Tuple[str, str], ModelVersion] = {}

    def register(
        self,
        model_name: str = "",
        model_version: str = "",
        experiment_id: str = "",
        dataset_version: str = "",
        metrics: Optional[Dict[str, float]] = None,
        status: ModelStatus = ModelStatus.CREATED,
    ) -> ModelVersion:
        """Register a model version with metadata. Supports both legacy and Phase 4.5 API styles."""

        # Legacy call: register("v2", {"accuracy": .9})
        if isinstance(model_version, dict) and not isinstance(experiment_id, str):
            legacy_metrics = model_version
            model_name, model_version = model_name, model_name
            experiment_id = ""
            dataset_version = ""
            metrics = legacy_metrics
            status = ModelStatus.CREATED

        # Legacy call: register("v2", metrics)
        if isinstance(model_version, dict) and isinstance(experiment_id, str):
            legacy_metrics = model_version
            metrics = legacy_metrics
            model_version = model_name
            model_name = "unknown_model"

        if not model_name:
            model_name = "unknown_model"
        if not model_version:
            model_version = "v1"

        version = ModelVersion(
            model_name=model_name,
            model_version=model_version,
            experiment_id=experiment_id,
            dataset_version=dataset_version,
            metrics=metrics or {},
            status=status,
        )
        self.versions[model_version] = version
        self.models[(model_name, model_version)] = version
        return version

    def list_versions(self) -> List[str]:
        return list(self.versions.keys())

    def get(self, model_name: Optional[str] = None, model_version: Optional[str] = None) -> Optional[ModelVersion]:
        """Query by model/version or version only for compatibility."""
        if model_name and model_version:
            return self.models.get((model_name, model_version))
        if model_version:
            return self.versions.get(model_version)
        return None

    def update_status(self, model_name: str, model_version: str, status: ModelStatus) -> Optional[ModelVersion]:
        model = self.models.get((model_name, model_version))
        if model:
            model.status = status
        return model

    def list_registered_models(self) -> List[ModelVersion]:
        return list(self.versions.values())
