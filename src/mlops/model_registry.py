from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RegisteredModel:
    model_version: str
    metadata: Dict[str, float]


class ModelRegistry:
    """Simple in-memory model registry for v1/v2 comparisons and rollout tracking."""

    def __init__(self):
        self.versions: Dict[str, RegisteredModel] = {}

    def register(self, version: str, metadata: Dict[str, float]) -> RegisteredModel:
        model = RegisteredModel(model_version=version, metadata=metadata)
        self.versions[version] = model
        return model

    def list_versions(self) -> List[str]:
        return list(self.versions.keys())

    def get(self, version: str) -> Optional[RegisteredModel]:
        return self.versions.get(version)
