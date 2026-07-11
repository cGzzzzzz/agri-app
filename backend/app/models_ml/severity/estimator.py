import logging
from pathlib import Path

import numpy as np

from app.models_ml.errors import ModelInferenceError, ModelUnavailableError
from app.vision.types import XAISeverity

logger = logging.getLogger(__name__)

_severity_session = None
_severity_input_name = None


def _get_severity_session():
    global _severity_session, _severity_input_name
    if _severity_session is not None:
        return _severity_session, _severity_input_name
    try:
        import onnxruntime as ort

        from app.config import get_settings

        settings = get_settings()
        onnx_path = settings.model_artifacts_dir / "severity_estimator" / "1.0.0" / "model.onnx"
        if not onnx_path.exists():
            logger.info("Severity ONNX not found at %s", onnx_path)
            return None, None
        session = ort.InferenceSession(str(onnx_path))
        _severity_session = session
        _severity_input_name = session.get_inputs()[0].name
        logger.info("Loaded severity ONNX from %s", onnx_path)
        return _severity_session, _severity_input_name
    except Exception:
        logger.warning("Failed to load severity ONNX", exc_info=True)
        return None, None


class ONNXSeverityEstimator:
    model_name = "severity-onnx-estimator"
    severity_classes = ["none", "low", "moderate", "high"]

    def __init__(self, session=None, input_name: str | None = None):
        if session is not None:
            self.session = session
            self.input_name = input_name or (session.get_inputs()[0].name if session else None)
        else:
            self.session, self.input_name = _get_severity_session()

    def predict(self, crop: str, disease: str, image: Path) -> XAISeverity:
        if self.session is None:
            raise ModelUnavailableError(
                "severity_estimation",
                crop,
                "Artifact or ONNX runtime is unavailable for severity_estimator.",
            )

        try:
            tensor = self._preprocess(image)
            outputs = self.session.run(None, {self.input_name: tensor})
            logits = outputs[1]
            probs = self._softmax(logits[0])
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])

            label = (
                self.severity_classes[pred_idx]
                if pred_idx < len(self.severity_classes)
                else "moderate"
            )

            evidence = [
                f"ONNX severity estimator prediction: {label} ({confidence:.2%})",
                f"Crop: {crop}, Disease: {disease}",
                f"Input image: {image.name}",
            ]
            rules_fired = ["onnx_model:severity_estimator"]

            return XAISeverity(
                label=label,
                score=confidence,
                evidence=evidence,
                rules_fired=rules_fired,
                model_name=self.model_name,
            )
        except Exception as exc:
            logger.exception("ONNX severity inference failed")
            raise ModelInferenceError(self.model_name, str(exc)) from exc

    def _preprocess(self, image_path: Path) -> np.ndarray:
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        img = img.resize((224, 224), Image.BILINEAR)
        arr = np.array(img, dtype=np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr - mean) / std
        arr = arr.transpose(2, 0, 1)
        return arr[np.newaxis, ...]

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()
