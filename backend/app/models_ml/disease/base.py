import logging
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from app.vision.types import XAIPrediction

logger = logging.getLogger(__name__)


class BaseDiseaseModel(ABC):
    def __init__(self, crop: str, class_names: list[str], model_name: str | None = None):
        self.crop = crop
        self.class_names = class_names
        self.model_name = model_name or f"{crop.lower()}_disease_model"

    @abstractmethod
    def _load_session(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _get_artifact_path(self) -> Path | None:
        raise NotImplementedError

    def predict(self, image: Path) -> XAIPrediction:
        session = self._try_load_session()
        if session is None:
            return self._baseline_fallback(image)

        try:
            tensor = self._preprocess(image)
            input_name = session.get_inputs()[0].name
            outputs = session.run(None, {input_name: tensor})
            logits = outputs[0]
            probs = self._softmax(logits[0])
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])

            label = self.class_names[pred_idx] if pred_idx < len(self.class_names) else self.class_names[0]

            evidence = [
                f"ONNX disease classifier ({self.crop}) prediction: {label} ({confidence:.2%})",
                f"Input image: {image.name}",
                f"Model classes: {', '.join(self.class_names)}",
            ]
            rules_fired = [f"onnx_model:{self.model_name}"]

            return XAIPrediction(
                label=label,
                confidence=confidence,
                evidence=evidence,
                rules_fired=rules_fired,
                heatmap_hint="Disease regions identified by neural network classifier.",
                model_name=self.model_name,
            )
        except Exception:
            logger.warning("ONNX disease inference failed for %s, falling back", self.crop, exc_info=True)
            return self._baseline_fallback(image)

    def _try_load_session(self):
        try:
            if not self._get_artifact_path():
                return None
            import onnxruntime as ort

            path = self._get_artifact_path()
            if path is None or not path.exists():
                return None
            return ort.InferenceSession(str(path))
        except Exception:
            return None

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

    def _baseline_fallback(self, image: Path) -> XAIPrediction:
        from app.vision.baselines import ExplainableDiseasePredictor
        return ExplainableDiseasePredictor().predict(self.crop, image)
