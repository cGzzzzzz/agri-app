"""
Evaluate trained ONNX disease classifiers on held-out test sets.

Usage:
    python -m app.models_ml.training.evaluate_test
    python -m app.models_ml.training.evaluate_test --crop Rice
    python -m app.models_ml.training.evaluate_test --data-dir data/prepared --artifacts artifacts
"""

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

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
    "Pepper": ["Bacterial Spot", "Healthy"],
}


def preprocess_image(image_path: Path) -> np.ndarray:
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    img = img.resize((224, 224), Image.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    arr = arr.transpose(2, 0, 1)
    return arr[np.newaxis, ...]


def softmax(x: np.ndarray) -> np.ndarray:
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


def load_onnx_session(onnx_path: Path):
    import onnxruntime as ort

    return ort.InferenceSession(str(onnx_path))


def evaluate_crop(crop: str, class_names: list[str], test_dir: Path, onnx_path: Path):
    session = load_onnx_session(onnx_path)
    input_name = session.get_inputs()[0].name

    true_labels = []
    pred_labels = []
    confidences = []
    per_class_correct = defaultdict(int)
    per_class_total = defaultdict(int)
    misclassified = []

    img_count = 0
    t0 = time.time()

    for class_dir in sorted(test_dir.iterdir()):
        if not class_dir.is_dir():
            continue
        gt_label = class_dir.name
        images = list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png"))
        for img_path in images:
            try:
                tensor = preprocess_image(img_path)
                outputs = session.run(None, {input_name: tensor})
                logits = outputs[0]
                probs = softmax(logits[0])
                pred_idx = int(np.argmax(probs))
                confidence = float(probs[pred_idx])
                pred_label = (
                    class_names[pred_idx] if pred_idx < len(class_names) else class_names[0]
                )

                true_labels.append(gt_label)
                pred_labels.append(pred_label)
                confidences.append(confidence)
                per_class_total[gt_label] += 1
                img_count += 1

                if pred_label == gt_label:
                    per_class_correct[gt_label] += 1
                else:
                    misclassified.append((img_path.name, gt_label, pred_label, confidence))
            except Exception as e:
                logger.warning("Failed to process %s: %s", img_path, e)

    elapsed = time.time() - t0
    total = len(true_labels)
    correct = sum(per_class_correct.values())
    overall_acc = correct / max(total, 1)

    avg_conf = np.mean(confidences) if confidences else 0
    correct_conf = (
        np.mean(
            [c for c, t, p in zip(confidences, true_labels, pred_labels, strict=False) if t == p]
        )
        if correct > 0
        else 0
    )
    wrong_conf = (
        np.mean(
            [c for c, t, p in zip(confidences, true_labels, pred_labels, strict=False) if t != p]
        )
        if (total - correct) > 0
        else 0
    )

    logger.info("")
    logger.info("=" * 70)
    logger.info("  TEST RESULTS: %s (%d images, %.1fs)", crop, total, elapsed)
    logger.info("=" * 70)
    logger.info("  Overall Accuracy: %d/%d = %.2f%%", correct, total, overall_acc * 100)
    logger.info(
        "  Avg Confidence: %.2f%% (correct: %.2f%%, wrong: %.2f%%)",
        avg_conf * 100,
        correct_conf * 100,
        wrong_conf * 100,
    )
    logger.info("  Throughput: %.0f images/sec", total / max(elapsed, 0.001))
    logger.info("")
    logger.info(
        "  %-30s %6s %6s %6s %6s %6s", "Class", "Total", "Correct", "Wrong", "Acc%", "AvgConf%"
    )
    logger.info("  " + "-" * 66)

    for cls in class_names:
        c = per_class_correct[cls]
        t = per_class_total[cls]
        w = t - c
        acc = c / max(t, 1) * 100
        cls_conf = (
            np.mean(
                [
                    co
                    for co, tr, pr in zip(confidences, true_labels, pred_labels, strict=False)
                    if tr == cls and pr == cls
                ]
            )
            * 100
            if c > 0
            else 0
        )
        logger.info("  %-30s %6d %6d %6d %5.1f%% %6.1f%%", cls, t, c, w, acc, cls_conf)

    logger.info("  " + "-" * 66)

    if misclassified:
        logger.info("")
        logger.info("  Top misclassifications:")
        misclass_counts = defaultdict(int)
        for _, gt, pred, _ in misclassified:
            misclass_counts[(gt, pred)] += 1
        for (gt, pred), count in sorted(misclass_counts.items(), key=lambda x: -x[1])[:5]:
            logger.info("    %s -> %s: %d times", gt, pred, count)

    cm = defaultdict(lambda: defaultdict(int))
    for true, pred in zip(true_labels, pred_labels, strict=False):
        cm[true][pred] += 1

    logger.info("")
    logger.info("  Confusion Matrix:")
    short_names = {c: c[:12] for c in class_names}
    header = "  {:>12s}".format("") + "".join(f"{short_names[c][:12]:>13s}" for c in class_names)
    logger.info(header)
    for true_cls in class_names:
        row = f"  {short_names[true_cls][:12]:>12s}"
        for pred_cls in class_names:
            val = cm[true_cls][pred_cls]
            row += f"{val:>13d}"
        logger.info(row)

    return {
        "crop": crop,
        "total": total,
        "correct": correct,
        "accuracy": round(overall_acc, 4),
        "avg_confidence": round(float(avg_conf), 4),
        "throughput_fps": round(total / max(elapsed, 0.001), 1),
        "per_class": {
            cls: {
                "total": per_class_total[cls],
                "correct": per_class_correct[cls],
                "accuracy": round(per_class_correct[cls] / max(per_class_total[cls], 1), 4),
            }
            for cls in class_names
        },
        "top_misclassified": [
            {"true": gt, "pred": pred, "count": cnt}
            for (gt, pred), cnt in sorted(misclass_counts.items(), key=lambda x: -x[1])[:5]
        ]
        if misclassified
        else [],
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate ONNX models on test sets")
    parser.add_argument("--data-dir", type=str, default="data/prepared")
    parser.add_argument("--artifacts", type=str, default="artifacts")
    parser.add_argument("--crop", type=str, nargs="*", help="Specific crops (default: all)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    artifacts_dir = Path(args.artifacts)

    crops_to_eval = args.crop if args.crop else list(CROP_DISEASE_MAP.keys())
    all_results = []
    total_correct = 0
    total_images = 0

    for crop in crops_to_eval:
        if crop not in CROP_DISEASE_MAP:
            logger.warning("Unknown crop: %s", crop)
            continue

        class_names = CROP_DISEASE_MAP[crop]
        test_dir = data_dir / crop / "test"
        onnx_path = artifacts_dir / f"{crop}_disease_model" / "1.0.0" / "model.onnx"

        if not test_dir.exists():
            logger.warning("No test dir for %s: %s", crop, test_dir)
            continue
        if not onnx_path.exists():
            logger.warning("No ONNX model for %s: %s", crop, onnx_path)
            continue

        result = evaluate_crop(crop, class_names, test_dir, onnx_path)
        all_results.append(result)
        total_correct += result["correct"]
        total_images += result["total"]

    if all_results:
        logger.info("")
        logger.info("=" * 70)
        logger.info("  OVERALL SUMMARY")
        logger.info("=" * 70)
        logger.info("")
        logger.info("  %-15s %8s %8s %8s %10s", "Crop", "Images", "Correct", "Wrong", "Accuracy")
        logger.info("  " + "-" * 53)
        for r in all_results:
            wrong = r["total"] - r["correct"]
            logger.info(
                "  %-15s %8d %8d %8d %7.2f%%",
                r["crop"],
                r["total"],
                r["correct"],
                wrong,
                r["accuracy"] * 100,
            )
        logger.info("  " + "-" * 53)
        overall = total_correct / max(total_images, 1) * 100
        logger.info(
            "  %-15s %8d %8d %8d %7.2f%%",
            "WEIGHTED TOTAL",
            total_images,
            total_correct,
            total_images - total_correct,
            overall,
        )

        report_path = artifacts_dir / "test_evaluation.json"
        report = {
            "per_crop": all_results,
            "overall": {
                "total_images": total_images,
                "total_correct": total_correct,
                "accuracy": round(total_correct / max(total_images, 1), 4),
            },
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("")
        logger.info("  Report saved to: %s", report_path)


if __name__ == "__main__":
    main()
