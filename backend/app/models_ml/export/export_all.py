"""
Export all models to ONNX format.

Usage:
    python -m app.models_ml.export.export_all

This will create ONNX artifacts for all crop disease classifiers and the severity estimator
under the artifacts/ directory.
"""

import argparse
import logging
from pathlib import Path

from app.models_ml.export.onnx_exporter import OnnxExporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CROPS = {
    "Rice": [
        "Healthy",
        "Rice Blast",
        "Bacterial Leaf Blight",
        "Brown Spot",
        "Leaf Sheath Blight",
        "Tungro",
    ],
    "Tomato": [
        "Healthy",
        "Early Blight",
        "Late Blight",
        "Septoria Leaf Spot",
        "Tomato Mosaic Virus",
        "Yellow Leaf Curl Virus",
        "Bacterial Spot",
        "Leaf Mold",
    ],
    "Banana": [
        "Healthy",
        "Black Sigatoka",
        "Fusarium Wilt",
        "Banana Bunchy Top Virus",
        "Cordana Leaf Spot",
        "Pestalotiopsis Leaf Spot",
    ],
    "Wheat": [
        "Healthy",
        "Leaf Rust",
        "Stripe Rust",
        "Powdery Mildew",
        "Septoria Leaf Blotch",
        "Tan Spot",
    ],
    "Corn": [
        "Healthy",
        "Northern Leaf Blight",
        "Gray Leaf Spot",
        "Common Rust",
        "Southern Rust",
        "Maize Dwarf Mosaic Virus",
    ],
}


def main():
    parser = argparse.ArgumentParser(description="Export all AgriAI models to ONNX")
    parser.add_argument(
        "--output-dir", type=str, default="artifacts", help="Output directory for ONNX artifacts"
    )
    parser.add_argument("--version", type=str, default="1.0.0", help="Model version to export")
    parser.add_argument("--crops", nargs="*", help="Specific crops to export (default: all)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    exporter = OnnxExporter(output_dir)

    crops_config = DEFAULT_CROPS
    if args.crops:
        crops_config = {k: v for k, v in DEFAULT_CROPS.items() if k in args.crops}
        if not crops_config:
            logger.error("No matching crops found for: %s", args.crops)
            return

    logger.info("Exporting %d crop disease classifiers + severity estimator", len(crops_config))
    results = exporter.export_all(crops_config, version=args.version)

    for name, path in results.items():
        logger.info("  %s -> %s", name, path)

    logger.info("Export complete. Artifacts written to %s", output_dir.resolve())


if __name__ == "__main__":
    main()
