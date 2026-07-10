import logging
from pathlib import Path

import numpy as np

from app.vision.types import XAISeverity

logger = logging.getLogger(__name__)


class ONNXSeverityEstimator:
    model_name = "severity-onnx-estimator"
    severity_classes = ["none", "low", "moderate", "high"]

    def __init__(self, session=None, input_name: str | None = None):
        self.session = session
        self.input_name = input_name
        if session and self.input_name is None:
            self.input_name = session.get_inputs()[0].name

    def predict(self, crop: str, disease: str, image: Path) -> XAISeverity:
        if self.session is None:
            return self._fallback(crop, disease, image)

        try:
            tensor = self._preprocess(image)
            outputs = self.session.run(None, {self.input_name: tensor})
            logits = outputs[0]
            probs = self._softmax(logits[0])
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])

            label = self.severity_classes[pred_idx] if pred_idx < len(self.severity_classes) else "moderate"

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
        except Exception:
            logger.warning("ONNX severity inference failed, falling back to baseline", exc_info=True)
            return self._fallback(crop, disease, image)

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

    def _fallback(self, crop: str, disease: str, image: Path) -> XAISeverity:
        from app.vision.baselines import ExplainableSeverityPredictor
        return ExplainableSeverityPredictor().predict(crop, disease, image)
