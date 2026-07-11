import numpy as np
import torch

from app.models_ml.architectures.classification.crop_classifier import CropClassifier
from app.models_ml.architectures.classification.efficientnet_classifier import DiseaseClassifier
from app.models_ml.architectures.severity.severity_model import SeverityModel
from app.models_ml.architectures.shared import (
    compute_lesion_area_ratio,
    crop_region,
    numpy_to_tensor,
)


class HybridVisionResult:
    def __init__(self):
        self.detections: list = []
        self.lesion_patches: list[np.ndarray] = []
        self.crop_prediction: str = ""
        self.crop_confidence: float = 0.0
        self.disease_prediction: str = ""
        self.disease_confidence: float = 0.0
        self.disease_probabilities: dict[str, float] = {}
        self.severity_score: float = 0.0
        self.severity_label: str = ""
        self.severity_probabilities: dict[str, float] = {}
        self.lesion_area_ratio: float = 0.0
        self.lesion_count: int = 0
        self.attention_map: torch.Tensor | None = None
        self.xai_available: bool = False


class HybridVisionPipeline:
    def __init__(
        self,
        yolo_detector=None,
        crop_classifier: CropClassifier | None = None,
        disease_classifiers: dict[str, DiseaseClassifier] | None = None,
        severity_model: SeverityModel | None = None,
        device: str = "cpu",
    ):
        self.detector = yolo_detector
        self.crop_classifier = crop_classifier
        self.disease_classifiers = disease_classifiers or {}
        self.severity_model = severity_model
        self.device = device

    def analyze(self, image: np.ndarray, crop_override: str | None = None) -> HybridVisionResult:
        result = HybridVisionResult()
        h, w = image.shape[:2]
        image_area = h * w

        if self.detector is not None:
            try:
                result.detections = self.detector.detect(image)
                result.lesion_count = len(
                    [d for d in result.detections if d.class_label != "healthy_leaf"]
                )
            except Exception:
                result.detections = []

        result.lesion_area_ratio = compute_lesion_area_ratio(result.detections, image_area)

        if crop_override:
            result.crop_prediction = crop_override
            result.crop_confidence = 1.0
        elif self.crop_classifier is not None:
            try:
                tensor = numpy_to_tensor(image)
                tensor = tensor.to(self.device)
                crop_name, crop_conf, _ = self.crop_classifier.predict(tensor)
                result.crop_prediction = crop_name
                result.crop_confidence = crop_conf
            except Exception:
                result.crop_prediction = "Rice"
                result.crop_confidence = 0.5

        if result.detections:
            for det in result.detections:
                if det.class_label != "healthy_leaf":
                    patch = crop_region(image, det.bbox)
                    if patch.size > 0:
                        result.lesion_patches.append(patch)

        if result.lesion_patches and self.disease_classifiers:
            crop_key = result.crop_prediction.lower()
            classifier = self.disease_classifiers.get(crop_key)
            if classifier is not None:
                try:
                    best_patch = max(result.lesion_patches, key=lambda p: p.size)
                    tensor = numpy_to_tensor(best_patch)
                    tensor = tensor.to(self.device)
                    disease_name, disease_conf, disease_probs = classifier.predict_with_confidence(
                        tensor
                    )
                    result.disease_prediction = disease_name
                    result.disease_confidence = disease_conf
                    result.disease_probabilities = disease_probs
                except Exception:
                    pass

        if not result.disease_prediction:
            result.disease_prediction = "Unknown"
            result.disease_confidence = 0.0

        if self.severity_model is not None:
            try:
                tensor = numpy_to_tensor(image)
                tensor = tensor.to(self.device)
                sev_score, sev_label, sev_probs = self.severity_model.predict(tensor)
                result.severity_score = sev_score
                result.severity_label = sev_label
                result.severity_probabilities = sev_probs
            except Exception:
                pass

        if not result.severity_label:
            if result.lesion_area_ratio > 0.3:
                result.severity_label = "high"
                result.severity_score = 0.8
            elif result.lesion_area_ratio > 0.1:
                result.severity_label = "moderate"
                result.severity_score = 0.5
            elif result.lesion_area_ratio > 0:
                result.severity_label = "low"
                result.severity_score = 0.2
            else:
                result.severity_label = "none"
                result.severity_score = 0.05

        if self.severity_model is not None or self.crop_classifier is not None:
            try:
                tensor = numpy_to_tensor(image).to(self.device)
                if self.severity_model:
                    result.attention_map = self.severity_model.get_attention_map(tensor)
                result.xai_available = True
            except Exception:
                pass

        return result
