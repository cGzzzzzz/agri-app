import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ClassificationMetrics:
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    per_class_precision: dict[str, float] = field(default_factory=dict)
    per_class_recall: dict[str, float] = field(default_factory=dict)
    per_class_f1: dict[str, float] = field(default_factory=dict)
    confusion_matrix: list[list[int]] = field(default_factory=list)
    total_samples: int = 0

    def to_dict(self) -> dict:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "per_class_precision": self.per_class_precision,
            "per_class_recall": self.per_class_recall,
            "per_class_f1": self.per_class_f1,
            "confusion_matrix": self.confusion_matrix,
            "total_samples": self.total_samples,
        }


@dataclass
class RegressionMetrics:
    mae: float = 0.0
    rmse: float = 0.0
    r_squared: float = 0.0
    total_samples: int = 0

    def to_dict(self) -> dict:
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "r_squared": self.r_squared,
            "total_samples": self.total_samples,
        }


@dataclass
class EvalReport:
    model_name: str
    model_version: str
    task: str
    class_names: list[str]
    classification: ClassificationMetrics | None = None
    regression: RegressionMetrics | None = None
    eval_loss: float = 0.0
    eval_duration_ms: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "task": self.task,
            "class_names": self.class_names,
            "classification": self.classification.to_dict() if self.classification else None,
            "regression": self.regression.to_dict() if self.regression else None,
            "eval_loss": self.eval_loss,
            "eval_duration_ms": self.eval_duration_ms,
            "notes": self.notes,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ModelEvaluator:
    def __init__(self):
        self._predictions: list[np.ndarray] = []
        self._labels: list[np.ndarray] = []

    def reset(self) -> None:
        self._predictions.clear()
        self._labels.clear()

    def add_batch(self, predictions: np.ndarray, labels: np.ndarray) -> None:
        self._predictions.append(predictions)
        self._labels.append(labels)

    def evaluate_classification(
        self,
        model_name: str,
        model_version: str,
        class_names: list[str],
        predictions: np.ndarray | None = None,
        labels: np.ndarray | None = None,
    ) -> EvalReport:
        if predictions is not None and labels is not None:
            self.reset()
            self.add_batch(predictions, labels)

        all_preds = np.concatenate(self._predictions) if self._predictions else np.array([])
        all_labels = np.concatenate(self._labels) if self._labels else np.array([])

        if len(all_preds) == 0 or len(all_labels) == 0:
            return EvalReport(
                model_name=model_name,
                model_version=model_version,
                task="classification",
                class_names=class_names,
                notes="No evaluation data provided",
            )

        metrics = self._compute_classification_metrics(all_preds, all_labels, class_names)

        return EvalReport(
            model_name=model_name,
            model_version=model_version,
            task="classification",
            class_names=class_names,
            classification=metrics,
            total_samples=len(all_labels),
        )

    def evaluate_regression(
        self,
        model_name: str,
        model_version: str,
        predictions: np.ndarray | None = None,
        labels: np.ndarray | None = None,
    ) -> EvalReport:
        if predictions is not None and labels is not None:
            self.reset()
            self.add_batch(predictions, labels)

        all_preds = np.concatenate(self._predictions) if self._predictions else np.array([])
        all_labels = np.concatenate(self._labels) if self._labels else np.array([])

        if len(all_preds) == 0 or len(all_labels) == 0:
            return EvalReport(
                model_name=model_name,
                model_version=model_version,
                task="regression",
                class_names=[],
                notes="No evaluation data provided",
            )

        mae = float(np.mean(np.abs(all_preds - all_labels)))
        rmse = float(np.sqrt(np.mean((all_preds - all_labels) ** 2)))
        ss_res = float(np.sum((all_labels - all_preds) ** 2))
        ss_tot = float(np.sum((all_labels - np.mean(all_labels)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        metrics = RegressionMetrics(
            mae=mae,
            rmse=rmse,
            r_squared=max(0.0, r_squared),
            total_samples=len(all_labels),
        )

        return EvalReport(
            model_name=model_name,
            model_version=model_version,
            task="regression",
            class_names=[],
            regression=metrics,
            total_samples=len(all_labels),
        )

    def _compute_classification_metrics(
        self,
        predictions: np.ndarray,
        labels: np.ndarray,
        class_names: list[str],
    ) -> ClassificationMetrics:
        num_classes = len(class_names)
        correct = int(np.sum(predictions == labels))
        total = len(labels)
        accuracy = correct / total if total > 0 else 0.0

        confusion = [[0] * num_classes for _ in range(num_classes)]
        for pred, label in zip(predictions, labels):
            pred_idx = int(pred) if isinstance(pred, (np.integer, int)) else int(np.argmax(pred))
            label_idx = int(label) if isinstance(label, (np.integer, int)) else int(label)
            if 0 <= pred_idx < num_classes and 0 <= label_idx < num_classes:
                confusion[label_idx][pred_idx] += 1

        per_class_precision = {}
        per_class_recall = {}
        per_class_f1 = {}
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0

        for i, name in enumerate(class_names):
            tp = confusion[i][i]
            fp = sum(confusion[j][i] for j in range(num_classes)) - tp
            fn = sum(confusion[i]) - tp

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            per_class_precision[name] = precision
            per_class_recall[name] = recall
            per_class_f1[name] = f1
            total_precision += precision
            total_recall += recall
            total_f1 += f1

        n = max(num_classes, 1)
        return ClassificationMetrics(
            accuracy=accuracy,
            precision=total_precision / n,
            recall=total_recall / n,
            f1=total_f1 / n,
            per_class_precision=per_class_precision,
            per_class_recall=per_class_recall,
            per_class_f1=per_class_f1,
            confusion_matrix=confusion,
            total_samples=total,
        )

    def save_report(self, report: EvalReport, output_path: Path | str) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.to_json(), encoding="utf-8")
        logger.info("Saved evaluation report: %s", path)
        return path
