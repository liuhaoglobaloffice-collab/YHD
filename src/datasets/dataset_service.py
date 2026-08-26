from typing import List, Optional

from .dataset_model import Dataset, TrainingSample


class DatasetService:
    """Minimal training dataset registry with a lightweight in-memory dataset store."""

    def __init__(self):
        self.datasets: List[Dataset] = []

    def create_dataset(self, name: str, version: str = "v1") -> Dataset:
        dataset = Dataset(name=name, version=version)
        self.datasets.append(dataset)
        return dataset

    def add_sample(self, dataset: Dataset, sample: TrainingSample) -> Dataset:
        dataset.samples.append(sample)
        return dataset

    def list(self) -> List[Dataset]:
        return list(self.datasets)

    def get(self, name: str) -> Optional[Dataset]:
        for dataset in self.datasets:
            if dataset.name == name:
                return dataset
        return None
