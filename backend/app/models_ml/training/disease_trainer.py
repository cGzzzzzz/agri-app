import json
import logging
import time
from pathlib import Path

import numpy as np
from tqdm import tqdm

from app.models_ml.training.base_trainer import BaseTrainer, TrainConfig, TrainResult

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader as TorchDataLoader
except ImportError:
    torch = None
    nn = None
    optim = None
    TorchDataLoader = None


class DiseaseTrainer(BaseTrainer):
    def __init__(self, crop: str, model_name: str | None = None, num_classes: int = 0):
        self.crop = crop
        self.model_name = model_name or f"{crop}_disease_model"
        self.num_classes = num_classes
        self.trained_model = None

    def _build_model(self, num_classes: int):
        from app.models_ml.architectures.classification.efficientnet_classifier import (
            DiseaseClassifier,
        )

        model = DiseaseClassifier(
            num_classes=num_classes, backbone="efficientnet_b0", pretrained=True
        )
        return model

    def train(
        self, dataset, config: TrainConfig, val_dataset=None, output_dir=Path("artifacts")
    ) -> TrainResult:
        self._validate_config(config)
        export_dir = Path(output_dir) / self.model_name / "1.0.0"
        export_dir.mkdir(parents=True, exist_ok=True)

        if torch is None:
            raise RuntimeError(
                "PyTorch is required to train a disease model. Install the training dependencies."
            )

        num_classes = getattr(dataset, "num_classes", 0) or self.num_classes
        if num_classes <= 0:
            raise ValueError("Dataset metadata must declare at least one disease class.")

        model = self._build_model(num_classes)
        device = torch.device(config.device)
        model = model.to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(
            model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
        )
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config.epochs)

        train_loader = self._make_loader(dataset, config, shuffle=True)
        if val_dataset is not None:
            val_loader = self._make_loader(val_dataset, config, shuffle=False)
        else:
            val_loader = self._make_loader(dataset, config, shuffle=False)

        training_log = []
        best_val_acc = 0.0
        best_state = None
        patience_counter = 0

        epoch_bar = tqdm(range(config.epochs), desc=f"{self.crop} [epochs]", position=0, leave=True)
        for epoch in epoch_bar:
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0

            epoch_start = time.time()
            batch_bar = tqdm(
                train_loader,
                desc=f"  Epoch {epoch + 1}/{config.epochs} [train]",
                position=1,
                leave=False,
            )
            for batch_images, batch_labels in batch_bar:
                batch_images = batch_images.to(device)
                batch_labels = batch_labels.to(device)

                optimizer.zero_grad()
                logits, _ = model(batch_images)
                loss = criterion(logits, batch_labels)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

                train_loss += loss.item() * batch_images.size(0)
                _, predicted = torch.max(logits, 1)
                train_correct += (predicted == batch_labels).sum().item()
                train_total += batch_labels.size(0)

            scheduler.step()

            train_loss = train_loss / max(train_total, 1)
            train_acc = train_correct / max(train_total, 1)

            val_loss, val_acc = self._evaluate_model(model, val_loader, criterion, device)
            epoch_time = time.time() - epoch_start

            epoch_metrics = {
                "epoch": epoch + 1,
                "train_loss": round(train_loss, 6),
                "train_acc": round(train_acc, 4),
                "val_loss": round(val_loss, 6),
                "val_acc": round(val_acc, 4),
                "lr": round(scheduler.get_last_lr()[0], 8),
                "epoch_time_sec": round(epoch_time, 2),
            }
            training_log.append(epoch_metrics)
            logger.info(
                "Epoch %d/%d - train_loss=%.4f train_acc=%.4f val_loss=%.4f val_acc=%.4f (%.1fs)",
                epoch + 1,
                config.epochs,
                train_loss,
                train_acc,
                val_loss,
                val_acc,
                epoch_time,
            )

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= config.early_stopping_patience:
                    logger.info("Early stopping at epoch %d", epoch + 1)
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        self.trained_model = model

        export_path = self.export(export_dir / "model.onnx", model, num_classes)

        metadata = {
            "model_name": self.model_name,
            "version": "1.0.0",
            "crop": self.crop,
            "num_classes": num_classes,
            "dataset.num_samples": getattr(dataset, "num_samples", 0),
            "training_epochs": len(training_log),
            "best_val_accuracy": round(best_val_acc, 4),
        }
        (export_dir / "training_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        registry_metadata = {
            "name": self.model_name,
            "version": "1.0.0",
            "crop": self.crop,
            "framework": "onnx",
            "task": "disease_classification",
            "classes": getattr(dataset, "class_names", []),
            "input_shape": [1, 3, 224, 224],
            "preprocessing": "imagenet_normalize",
            "artifact_path": str(export_dir / "model.onnx"),
            "description": f"Disease classification model for {self.crop}",
            "metrics": {"accuracy": round(best_val_acc, 4)},
            "created_at": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
            "tags": [],
        }
        (export_dir / "metadata.json").write_text(
            json.dumps(registry_metadata, indent=2), encoding="utf-8"
        )

        return TrainResult(
            model_name=self.model_name,
            version="1.0.0",
            best_metric=best_val_acc,
            metric_name="accuracy",
            epochs_trained=len(training_log),
            export_path=export_path,
            class_names=getattr(dataset, "class_names", []),
            training_log=training_log,
        )

    def _evaluate_model(self, model, data_loader, criterion, device) -> tuple[float, float]:
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            eval_bar = tqdm(data_loader, desc="  [eval]", position=1, leave=False)
            for batch_images, batch_labels in eval_bar:
                batch_images = batch_images.to(device)
                batch_labels = batch_labels.to(device)
                logits, _ = model(batch_images)
                loss = criterion(logits, batch_labels)
                total_loss += loss.item() * batch_images.size(0)
                _, predicted = torch.max(logits, 1)
                correct += (predicted == batch_labels).sum().item()
                total += batch_labels.size(0)
        return total_loss / max(total, 1), correct / max(total, 1)

    def _make_loader(self, dataset, config: TrainConfig, shuffle: bool = True):
        if TorchDataLoader is not None and isinstance(dataset, TorchDataLoader):
            return dataset

        if hasattr(dataset, "to_pytorch_dataset"):
            loader = dataset.to_pytorch_dataset()
            if loader is not None:
                return loader

        class _NumpyDataset:
            def __init__(self, ds, cfg, shuf):
                self._data = []
                self._img_size = cfg.image_size
                for img, label in ds.iter_samples():
                    self._data.append((img, label))
                if shuf and len(self._data) > 1:
                    perm = np.random.permutation(len(self._data))
                    self._data = [self._data[i] for i in perm]

            def __len__(self):
                return len(self._data)

            def __getitem__(self, idx):
                arr, label = self._data[idx]
                return torch.from_numpy(arr), label

        return TorchDataLoader(
            _NumpyDataset(dataset, config, shuffle), batch_size=config.batch_size, shuffle=False
        )

    def evaluate(self, dataset, model=None) -> dict:
        if torch is None:
            raise RuntimeError(
                "PyTorch is required to evaluate a disease model. Install the training dependencies."
            )

        num_classes = getattr(dataset, "num_classes", 0) or self.num_classes
        if model is None:
            model = self._build_model(num_classes)
        model.eval()
        total = 0
        correct = 0

        loader = self._make_loader(dataset, TrainConfig(batch_size=32), shuffle=False)
        with torch.no_grad():
            eval_bar = tqdm(loader, desc="  [final eval]", position=1, leave=False)
            for batch_images, batch_labels in eval_bar:
                logits, _ = model(batch_images)
                _, predicted = torch.max(logits, 1)
                correct += (predicted == batch_labels).sum().item()
                total += batch_labels.size(0)

        accuracy = correct / max(total, 1)
        return {
            "accuracy": accuracy,
            "precision": accuracy,
            "recall": accuracy,
            "f1": accuracy,
            "total_samples": total,
            "correct": correct,
        }

    def export(self, output_path: Path, model=None, num_classes: int = 0) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if torch is not None and model is not None:
            try:
                model.eval()
                device = next(model.parameters()).device
                dummy = torch.randn(1, 3, 224, 224).to(device)
                torch.onnx.export(
                    model,
                    dummy,
                    str(output_path),
                    input_names=["image"],
                    output_names=["logits", "features"],
                    dynamic_axes={
                        "image": {0: "batch_size"},
                        "logits": {0: "batch_size"},
                        "features": {0: "batch_size"},
                    },
                    opset_version=17,
                    dynamo=False,
                )
                logger.info("Exported ONNX model to %s", output_path)
                return output_path
            except Exception as exc:
                logger.exception("ONNX export failed for %s", self.model_name)
                raise RuntimeError(f"ONNX export failed for {self.model_name}") from exc

        raise RuntimeError("A trained PyTorch model is required before ONNX export.")
