"""
Train all disease classifiers and severity model.

Usage:
    python -m app.models_ml.training.run_training [--crop Rice] [--epochs 30] [--device cpu]

Crops trained: Rice, Tomato, Potato, Pepper (from available prepared data).
"""

import argparse
import json
import logging
import random
import sys
from pathlib import Path

from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


CROP_DISEASE_MAP = {
    "Rice": ["Bacterial Leaf Blight", "Brown Spot", "Rice Blast", "Leaf Smut", "Tungro"],
    "Tomato": [
        "Bacterial Spot",
        "Early Blight",
        "Late Blight",
        "Leaf Mold",
        "Septoria Leaf Spot",
        "Spider Mites",
        "Target Spot",
        "Yellow Leaf Curl Virus",
        "Tomato Mosaic Virus",
        "Healthy",
    ],
    "Potato": ["Early Blight", "Late Blight", "Healthy"],
    "Corn": ["Common Rust", "Northern Leaf Blight", "Gray Leaf Spot", "Healthy"],
    "Grape": ["Black Rot", "Leaf Blight", "Healthy"],
    "Pepper": ["Bacterial Spot", "Healthy"],
    "Apple": ["Black Rot", "Leaf Blight", "Healthy"],
    "Cherry": ["Powdery Mildew", "Healthy"],
    "Orange": ["Bacterial Spot"],
    "Peach": ["Bacterial Spot", "Healthy"],
    "Blueberry": ["Healthy"],
    "Squash": ["Powdery Mildew"],
}

SEVERITY_CLASSES = ["none", "low", "moderate", "high"]


def get_available_crops(data_dir: Path) -> list[str]:
    available = []
    for crop in CROP_DISEASE_MAP:
        crop_dir = data_dir / crop
        if crop_dir.exists():
            train_dir = crop_dir / "train"
            if train_dir.exists():
                available.append(crop)
    return available


def train_disease_classifier(crop: str, data_dir: Path, output_dir: Path, config):
    logger.info("=" * 60)
    logger.info("Training disease classifier for: %s", crop)
    logger.info("=" * 60)

    from app.models_ml.training.dataset.dataset_loader import DatasetLoader
    from app.models_ml.training.disease_trainer import DiseaseTrainer

    class_names = CROP_DISEASE_MAP[crop]
    train_dir = data_dir / crop / "train"
    val_dir = data_dir / crop / "val"

    if not train_dir.exists():
        logger.warning("No training data for %s at %s", crop, train_dir)
        return None

    train_loader = DatasetLoader(
        train_dir,
        class_names=class_names,
        image_size=(224, 224),
        batch_size=config.batch_size,
        shuffle=True,
    )
    val_loader = (
        DatasetLoader(
            val_dir,
            class_names=class_names,
            image_size=(224, 224),
            batch_size=config.batch_size,
            shuffle=False,
        )
        if val_dir.exists()
        else None
    )

    logger.info("  Train: %d images, Classes: %d", train_loader.num_samples, len(class_names))
    if val_loader:
        logger.info("  Val: %d images", val_loader.num_samples)
    for cls, count in train_loader.class_distribution().items():
        logger.info("    %s: %d", cls, count)

    from app.models_ml.training.base_trainer import TrainConfig

    trainer = DiseaseTrainer(crop=crop, num_classes=len(class_names))
    train_config = TrainConfig(
        epochs=config.epochs,
        batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        weight_decay=1e-5,
        image_size=(224, 224),
        num_workers=0,
        early_stopping_patience=5,
        device=config.device,
    )

    result = trainer.train(
        train_loader, train_config, val_dataset=val_loader, output_dir=output_dir
    )

    if val_loader:
        val_result = trainer.evaluate(val_loader, model=trainer.trained_model)
        logger.info(
            "  Validation: accuracy=%.4f, precision=%.4f, recall=%.4f, f1=%.4f",
            val_result.get("accuracy", 0),
            val_result.get("precision", 0),
            val_result.get("recall", 0),
            val_result.get("f1", 0),
        )

    return result


def train_severity_model(data_dir: Path, output_dir: Path, config):
    logger.info("=" * 60)
    logger.info("Training severity model (all crops combined)")
    logger.info("=" * 60)

    import numpy as np
    import torch
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset

    img_files = []
    for crop in CROP_DISEASE_MAP:
        crop_dir = data_dir / crop / "train"
        if not crop_dir.exists():
            continue
        for class_dir in crop_dir.iterdir():
            if not class_dir.is_dir():
                continue
            for img_path in class_dir.glob("*.jpg"):
                img_files.append((img_path, class_dir.name))

    if not img_files:
        logger.warning("No images found for severity training")
        return None

    def _get_severity(class_name):
        if "Healthy" in class_name:
            return 0

        _HIGH = {
            "Rice Blast",
            "Tungro",
            "Late Blight",
            "Yellow Leaf Curl Virus",
            "Northern Leaf Blight",
            "Black Rot",
            "Gray Leaf Spot",
        }
        _MODERATE = {
            "Bacterial Leaf Blight",
            "Bacterial Spot",
            "Early Blight",
            "Leaf Mold",
            "Septoria Leaf Spot",
            "Target Spot",
            "Tomato Mosaic Virus",
            "Common Rust",
            "Leaf Blight",
            "Spider Mites",
            "Powdery Mildew",
        }
        _LOW = {
            "Brown Spot",
            "Leaf Smut",
        }

        name = class_name.strip()
        if name in _HIGH:
            return 3
        if name in _MODERATE:
            return 2
        if name in _LOW:
            return 1
        return 2

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    class _LazySeverityDataset(Dataset):
        def __init__(self, file_list):
            self._files = file_list

        def __len__(self):
            return len(self._files)

        def __getitem__(self, idx):
            img_path, class_name = self._files[idx]
            label = _get_severity(class_name)
            img = Image.open(img_path).convert("RGB").resize((224, 224))
            arr = np.array(img, dtype=np.float32) / 255.0
            arr = (arr - mean) / std
            arr = arr.transpose(2, 0, 1)
            return torch.from_numpy(arr), label

    random.shuffle(img_files)
    n = len(img_files)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)

    train_files = img_files[:train_end]
    val_files = img_files[train_end:val_end]

    train_loader = DataLoader(
        _LazySeverityDataset(train_files), batch_size=config.batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        _LazySeverityDataset(val_files), batch_size=config.batch_size, shuffle=False, num_workers=0
    )

    logger.info("  Total images: %d (train=%d, val=%d)", n, len(train_files), len(val_files))

    severity_counts = {}
    for _, cn in img_files:
        sev = SEVERITY_CLASSES[_get_severity(cn)]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    for cls, count in sorted(severity_counts.items()):
        logger.info("    %s: %d", cls, count)

    from app.models_ml.training.base_trainer import TrainConfig
    from app.models_ml.training.severity_trainer import SeverityTrainer

    trainer = SeverityTrainer(model_name="severity_estimator")
    train_config = TrainConfig(
        epochs=config.epochs,
        batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        weight_decay=1e-5,
        image_size=(224, 224),
        num_workers=0,
        early_stopping_patience=5,
        device=config.device,
    )

    result = trainer.train(
        train_loader, train_config, val_dataset=val_loader, output_dir=output_dir
    )

    val_result = trainer.evaluate(val_loader, model=trainer.trained_model)
    logger.info(
        "  Validation: mae=%.4f, rmse=%.4f", val_result.get("mae", 0), val_result.get("rmse", 0)
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Train all AgriAI ML models")
    parser.add_argument(
        "--data-dir", type=str, default="data/prepared", help="Prepared data directory"
    )
    parser.add_argument(
        "--output-dir", type=str, default="artifacts", help="Output directory for ONNX artifacts"
    )
    parser.add_argument(
        "--crop", type=str, nargs="*", help="Specific crops to train (default: all available)"
    )
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu/cuda)")
    parser.add_argument("--severity-only", action="store_true", help="Train only severity model")
    parser.add_argument("--skip-severity", action="store_true", help="Skip severity model training")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists():
        logger.error("Data directory not found: %s", data_dir)
        logger.info("Run: python -m app.models_ml.training.prepare_plantvillage")
        return

    available_crops = get_available_crops(data_dir)
    logger.info("Available crops with training data: %s", available_crops)

    if not available_crops:
        logger.error("No training data found. Run prepare_plantvillage first.")
        return

    crops_to_train = args.crop if args.crop else available_crops
    crops_to_train = [c for c in crops_to_train if c in available_crops]

    if not args.severity_only:
        crop_bar = tqdm(crops_to_train, desc="Training crops", position=0, leave=True)
        for crop in crop_bar:
            crop_bar.set_postfix(crop=crop)
            try:
                train_disease_classifier(crop, data_dir, output_dir, args)
            except Exception as e:
                logger.error("Failed to train %s: %s", crop, e, exc_info=True)

    if not args.skip_severity:
        try:
            train_severity_model(data_dir, output_dir, args)
        except Exception as e:
            logger.error("Failed to train severity model: %s", e, exc_info=True)

    logger.info("=" * 60)
    logger.info("Training complete! Artifacts written to: %s", output_dir.resolve())
    logger.info("=" * 60)

    for item in output_dir.iterdir():
        if item.is_dir():
            onnx_file = item / "1.0.0" / "model.onnx"
            meta_file = item / "1.0.0" / "metadata.json"
            if onnx_file.exists():
                size_mb = onnx_file.stat().st_size / (1024 * 1024)
                logger.info("  %s: %.1f MB", item.name, size_mb)
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                if "best_val_accuracy" in meta:
                    logger.info("    val_accuracy: %.4f", meta["best_val_accuracy"])
                elif "best_val_mae" in meta:
                    logger.info("    val_mae: %.4f", meta["best_val_mae"])


if __name__ == "__main__":
    main()
