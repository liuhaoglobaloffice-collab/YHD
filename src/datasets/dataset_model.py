from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class TrainingSample:
    input: str
    context: str
    output: str
    label: str
    quality_score: float


@dataclass
class Dataset:
    name: str
    version: str = "v1"
    samples: List[TrainingSample] = field(default_factory=list)

    @classmethod
    def from_training_samples(cls, name: str, samples: List[TrainingSample], version: str = "v1"):
        return cls(name=name, version=version, samples=samples)
