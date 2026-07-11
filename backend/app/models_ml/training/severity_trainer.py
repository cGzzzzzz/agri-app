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


class SeverityTrainer(BaseTrainer):
    def __init__(self, model_name: str = "severity_estimator"):
        self.model_name = model_name
        self.trained_model = None

    def _build_model(self):
        from app.models_ml.architectures.severity.severity_model import SeverityModel

        return SeverityModel(backbone="efficientnet_b0", pretrained=True)

    def train(
        self, dataset, config: TrainConfig, val_dataset=None, output_dir=Path("artifacts")
    ) -> TrainResult:
        self._validate_config(config)
        export_dir = Path(output_dir) / self.model_name / "1.0.0"
        export_dir.mkdir(parents=True, exist_ok=True)

        if torch is None:
            raise RuntimeError(
                "PyTorch is required to train a severity model. Install the training dependencies."
            )

        model = self._build_model()
        device = torch.device(config.device)
        model = model.to(device)

        regression_criterion = nn.MSELoss()
        classification_criterion = nn.CrossEntropyLoss()
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
        best_val_mae = float("inf")
        best_state = None
        patience_counter = 0

        epoch_bar = tqdm(range(config.epochs), desc="Severity [epochs]", position=0, leave=True)
        for epoch in epoch_bar:
            model.train()
            train_loss = 0.0
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

                regression_targets = batch_labels.float().unsqueeze(1) / 3.0
                classification_targets = batch_labels

                optimizer.zero_grad()
                severity_score, severity_logits = model(batch_images)
                loss_reg = regression_criterion(severity_score, regression_targets)
                loss_cls = classification_criterion(severity_logits, classification_targets)
                loss = 0.5 * loss_reg + 0.5 * loss_cls
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

                train_loss += loss.item() * batch_images.size(0)
                train_total += batch_labels.size(0)

            scheduler.step()
            train_loss = train_loss / max(train_total, 1)

            val_mae, val_rmse = self._evaluate_model(model, val_loader, device)
            epoch_time = time.time() - epoch_start

            epoch_metrics = {
                "epoch": epoch + 1,
                "train_loss": round(train_loss, 6),
                "val_mae": round(val_mae, 6),
                "val_rmse": round(val_rmse, 6),
                "lr": round(scheduler.get_last_lr()[0], 8),
                "epoch_time_sec": round(epoch_time, 2),
            }
            training_log.append(epoch_metrics)
            logger.info(
                "Epoch %d/%d - train_loss=%.4f val_mae=%.4f val_rmse=%.4f (%.1fs)",
                epoch + 1,
                config.epochs,
                train_loss,
                val_mae,
                val_rmse,
                epoch_time,
            )

            if val_mae < best_val_mae:
                best_val_mae = val_mae
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

        export_path = self.export(export_dir / "model.onnx", model)

        if hasattr(dataset, "dataset"):
            num_samples = len(dataset.dataset)
        elif hasattr(dataset, "__len__"):
            num_samples = len(dataset)
        else:
            num_samples = 0

        metadata = {
            "model_name": self.model_name,
            "version": "1.0.0",
            "task": "severity",
            "dataset.num_samples": num_samples,
            "training_epochs": len(training_log),
            "best_val_mae": round(best_val_mae, 4),
        }
        (export_dir / "training_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        registry_metadata = {
            "name": self.model_name,
            "version": "1.0.0",
            "crop": "",
            "framework": "onnx",
            "task": "severity_estimation",
            "classes": ["none", "low", "moderate", "high"],
            "input_shape": [1, 3, 224, 224],
            "preprocessing": "imagenet_normalize",
            "artifact_path": str(export_dir / "model.onnx"),
            "description": "Severity estimation model for all crops",
            "metrics": {"mae": round(best_val_mae, 4)},
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
            best_metric=best_val_mae,
            metric_name="mae",
            epochs_trained=len(training_log),
            export_path=export_path,
            class_names=["none", "low", "moderate", "high"],
            training_log=training_log,
        )

    def _evaluate_model(self, model, data_loader, device) -> tuple[float, float]:
        model.eval()
        all_scores = []
        all_labels = []
        with torch.no_grad():
            eval_bar = tqdm(data_loader, desc="  [eval]", position=1, leave=False)
            for batch_images, batch_labels in eval_bar:
                batch_images = batch_images.to(device)
                severity_score, _ = model(batch_images)
                scores = severity_score.cpu().squeeze(-1).tolist()
                if isinstance(scores, float):
                    scores = [scores]
                all_scores.extend(scores)
                all_labels.extend(batch_labels.tolist())

        scores = np.array(all_scores)
        labels = np.array(all_labels) / 3.0
        mae = float(np.mean(np.abs(scores - labels)))
        rmse = float(np.sqrt(np.mean((scores - labels) ** 2)))
        return mae, rmse

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
                "PyTorch is required to evaluate a severity model. Install the training dependencies."
            )

        if model is None:
            model = self._build_model()
        model.eval()
        loader = self._make_loader(dataset, TrainConfig(batch_size=32), shuffle=False)
        device = next(model.parameters()).device
        mae, rmse = self._evaluate_model(model, loader, device)

        return {
            "mae": mae,
            "rmse": rmse,
            "r_squared": max(0.0, 1.0 - mae),
            "total_samples": getattr(dataset, "num_samples", 0),
        }

    def export(self, output_path: Path, model=None) -> Path:
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
                    output_names=["severity_score", "severity_logits"],
                    dynamic_axes={
                        "image": {0: "batch_size"},
                        "severity_score": {0: "batch_size"},
                        "severity_logits": {0: "batch_size"},
                    },
                    opset_version=17,
                    dynamo=False,
                )
                logger.info("Exported ONNX severity model to %s", output_path)
                return output_path
            except Exception as exc:
                logger.exception("ONNX export failed for %s", self.model_name)
                raise RuntimeError(f"ONNX export failed for {self.model_name}") from exc

        raise RuntimeError("A trained PyTorch model is required before ONNX export.")
