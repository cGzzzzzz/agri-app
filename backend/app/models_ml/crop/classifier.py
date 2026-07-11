import logging
from pathlib import Path

import numpy as np

from app.models_ml.errors import ModelInferenceError, ModelUnavailableError
from app.vision.types import XAIPrediction

logger = logging.getLogger(__name__)


class ONNXCropClassifier:
    model_name = "crop-onnx-classifier"

    def __init__(
        self, session=None, class_names: list[str] | None = None, input_name: str | None = None
    ):
        self.session = session
        self.class_names = class_names or ["Rice", "Tomato", "Wheat", "Maize", "Cotton"]
        self.input_name = input_name
        if session and self.input_name is None:
            self.input_name = session.get_inputs()[0].name

    def predict(self, image: Path) -> XAIPrediction:
        if self.session is None:
            raise ModelUnavailableError("crop_classification")

        try:
            tensor = self._preprocess(image)
            outputs = self.session.run(None, {self.input_name: tensor})
            logits = outputs[0]
            probs = self._softmax(logits[0])
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])

            if pred_idx < len(self.class_names):
                label = self.class_names[pred_idx]
            else:
                label = self.class_names[0]

            evidence = [
                f"ONNX crop classifier prediction: {label} ({confidence:.2%})",
                f"Input image: {image.name}",
                f"Model classes: {', '.join(self.class_names)}",
            ]
            rules_fired = ["onnx_model:crop_classifier"]

            return XAIPrediction(
                label=label,
                confidence=confidence,
                evidence=evidence,
                rules_fired=rules_fired,
                heatmap_hint="Crop region identified by neural network classifier.",
                model_name=self.model_name,
            )
        except Exception as exc:
            logger.exception("ONNX crop inference failed")
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
