import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import torch
except ImportError:
    torch = None


class OnnxExporter:
    def __init__(self, output_dir: Path | str = "artifacts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_disease_classifier(
        self,
        crop: str,
        num_classes: int,
        class_names: list[str],
        version: str = "1.0.0",
        input_shape: list[int] | None = None,
    ) -> Path:
        input_shape = input_shape or [1, 3, 224, 224]
        model_dir = self.output_dir / f"{crop}_disease_model" / version
        model_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = model_dir / "model.onnx"

        if torch is None:
            raise RuntimeError("PyTorch is required to export a disease model.")
        try:
            from app.models_ml.architectures.classification.efficientnet_classifier import (
                DiseaseClassifier,
            )

            model = DiseaseClassifier(
                num_classes=num_classes, backbone="efficientnet_b0", pretrained=False
            )
            model.eval()
            dummy = torch.randn(*input_shape)
            torch.onnx.export(
                model,
                dummy,
                str(onnx_path),
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
        except Exception as exc:
            logger.exception("ONNX export failed for %s", crop)
            raise RuntimeError(f"ONNX export failed for {crop}") from exc

        self._write_metadata(
            model_dir,
            name=f"{crop}_disease_model",
            version=version,
            crop=crop,
            task="disease_classification",
            classes=class_names,
            input_shape=input_shape,
        )

        logger.info("Exported disease classifier for %s to %s", crop, model_dir)
        return model_dir

    def export_severity_estimator(
        self,
        version: str = "1.0.0",
        input_shape: list[int] | None = None,
    ) -> Path:
        input_shape = input_shape or [1, 3, 224, 224]
        model_dir = self.output_dir / "severity_estimator" / version
        model_dir.mkdir(parents=True, exist_ok=True)
        onnx_path = model_dir / "model.onnx"

        if torch is None:
            raise RuntimeError("PyTorch is required to export a severity model.")
        try:
            from app.models_ml.architectures.severity.severity_model import SeverityModel

            model = SeverityModel(backbone="efficientnet_b0", pretrained=False)
            model.eval()
            dummy = torch.randn(*input_shape)
            torch.onnx.export(
                model,
                dummy,
                str(onnx_path),
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
        except Exception as exc:
            logger.exception("ONNX export failed for severity model")
            raise RuntimeError("ONNX export failed for severity_estimator") from exc

        self._write_metadata(
            model_dir,
            name="severity_estimator",
            version=version,
            crop="",
            task="severity_estimation",
            classes=["none", "low", "moderate", "high"],
            input_shape=input_shape,
        )

        logger.info("Exported severity estimator to %s", model_dir)
        return model_dir

    def _write_metadata(
        self,
        model_dir: Path,
        name: str,
        version: str,
        crop: str,
        task: str,
        classes: list[str],
        input_shape: list[int],
    ) -> None:
        metadata = {
            "name": name,
            "version": version,
            "crop": crop,
            "framework": "onnx",
            "task": task,
            "classes": classes,
            "input_shape": input_shape,
            "preprocessing": "imagenet_normalize",
            "artifact_path": str(model_dir / "model.onnx"),
            "description": f"{task} model for {crop}" if crop else f"{task} model",
            "metrics": {},
            "created_at": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
            "tags": [],
        }
        (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def export_all(
        self,
        crops_config: dict[str, list[str]],
        version: str = "1.0.0",
    ) -> dict[str, Path]:
        results = {}

        for crop, diseases in crops_config.items():
            results[crop] = self.export_disease_classifier(
                crop=crop,
                num_classes=len(diseases),
                class_names=diseases,
                version=version,
            )

        results["severity"] = self.export_severity_estimator(version=version)

        return results
