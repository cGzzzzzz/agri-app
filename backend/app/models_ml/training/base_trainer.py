from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TrainConfig:
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    image_size: tuple[int, int] = (224, 224)
    num_workers: int = 2
    early_stopping_patience: int = 5
    save_best_only: bool = True
    export_format: str = "onnx"
    device: str = "cpu"
    extra: dict = field(default_factory=dict)


@dataclass
class TrainResult:
    model_name: str
    version: str
    best_metric: float
    metric_name: str
    epochs_trained: int
    export_path: Path
    class_names: list[str]
    training_log: list[dict] = field(default_factory=list)


class BaseTrainer(ABC):
    @abstractmethod
    def train(self, dataset, config: TrainConfig) -> TrainResult:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, dataset) -> dict:
        raise NotImplementedError

    @abstractmethod
    def export(self, output_path: Path) -> Path:
        raise NotImplementedError

    def _validate_config(self, config: TrainConfig) -> None:
        if config.epochs <= 0:
            raise ValueError(f"epochs must be positive, got {config.epochs}")
        if config.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {config.batch_size}")
        if config.learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive, got {config.learning_rate}")
