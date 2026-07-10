import logging
from pathlib import Path

import numpy as np

from app.orchestrator.input_types import CropPrediction, DiseasePrediction, SeverityEstimation
from app.vision.baselines import ExplainableDiseasePredictor, ExplainableSeverityPredictor

logger = logging.getLogger(__name__)

_shared_hybrid_wrapper = None


def _get_hybrid_wrapper():
    global _shared_hybrid_wrapper
    if _shared_hybrid_wrapper is None:
        _shared_hybrid_wrapper = HybridOrchestratorWrapper()
    return _shared_hybrid_wrapper


class HybridOrchestratorWrapper:
    def __init__(self):
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from app.models_ml.architectures.hybrid_pipeline import HybridVisionPipeline

            self._pipeline = HybridVisionPipeline(device="cpu")
            return self._pipeline
        except Exception:
            logger.debug("HybridVisionPipeline not available", exc_info=True)
            return None

    def analyze_image(self, image_path: str, crop_override: str | None = None):
        pipeline = self._get_pipeline()
        if pipeline is None:
            return None

        try:
            from PIL import Image as PILImage

            img = PILImage.open(image_path).convert("RGB")
            img = img.resize((640, 640), PILImage.BILINEAR)
            image_arr = np.array(img)
        except Exception:
            logger.warning("Failed to load image for hybrid pipeline: %s", image_path)
            return None

        return pipeline.analyze(image_arr, crop_override=crop_override)


def get_or_run_hybrid(state: dict, image_path: str, crop_label: str):
    cached = state.get("_hybrid_result")
    if cached is not None:
        return cached
    wrapper = _get_hybrid_wrapper()
    result = wrapper.analyze_image(image_path, crop_override=crop_label)
    state["_hybrid_result"] = result
    return result


class DiseaseDetector:
    def __init__(self):
        self.baseline = ExplainableDiseasePredictor()

    def detect(self, state: dict) -> DiseasePrediction:
        crop: CropPrediction = state["crop_resolution"]
        processed = state.get("image_preprocessing")
        image_path = Path(state["input"].image_path)

        hybrid_result = get_or_run_hybrid(state, str(image_path), crop.label)

        if hybrid_result is not None and hybrid_result.disease_prediction:
            evidence = [
                f"Hybrid pipeline prediction: {hybrid_result.disease_prediction} "
                f"({hybrid_result.disease_confidence:.2%})",
                f"Crop context: {crop.label}",
                f"Lesions detected: {hybrid_result.lesion_count}",
                f"Lesion area ratio: {hybrid_result.lesion_area_ratio:.2%}",
            ]
            if hybrid_result.disease_probabilities:
                top_3 = sorted(
                    hybrid_result.disease_probabilities.items(),
                    key=lambda x: x[1], reverse=True,
                )[:3]
                evidence.append(
                    f"Top predictions: {', '.join(f'{k}: {v:.2%}' for k, v in top_3)}"
                )

            rules_fired = ["hybrid_pipeline:disease_classification"]
            if hybrid_result.detections:
                rules_fired.append(f"yolo_detections:{len(hybrid_result.detections)}")

            return DiseasePrediction(
                label=hybrid_result.disease_prediction,
                confidence=hybrid_result.disease_confidence,
                evidence=evidence,
                rules_fired=rules_fired,
                heatmap_hint="Focus on spot margins, chlorotic halos, lesion clustering, and necrotic leaf areas.",
                model_name="hybrid-vision-pipeline",
            )

        try:
            from app.models_ml.disease.registry import DiseaseModelRegistry

            onnx_pred = DiseaseModelRegistry.predict(crop.label, image_path)
            if onnx_pred is not None:
                return DiseasePrediction.from_xai(onnx_pred)
        except Exception:
            pass

        xai_pred = self.baseline.predict(crop.label, image_path)
        return DiseasePrediction.from_xai(xai_pred)


class SeverityEstimatorStage:
    def __init__(self):
        self.baseline = ExplainableSeverityPredictor()

    def estimate(self, state: dict) -> SeverityEstimation:
        crop: CropPrediction = state["crop_resolution"]
        disease: DiseasePrediction = state["disease_detection"]
        processed = state.get("image_preprocessing")
        image_path = Path(state["input"].image_path)

        hybrid_result = get_or_run_hybrid(state, str(image_path), crop.label)

        if hybrid_result is not None and hybrid_result.severity_label:
            evidence = [
                f"Hybrid pipeline severity: {hybrid_result.severity_label} "
                f"(score: {hybrid_result.severity_score:.2%})",
                f"Crop context: {crop.label}, Disease context: {disease.label}",
                f"Lesion area ratio: {hybrid_result.lesion_area_ratio:.2%}",
                f"Lesion count: {hybrid_result.lesion_count}",
            ]
            if hybrid_result.severity_probabilities:
                probs_str = ", ".join(
                    f"{k}: {v:.2%}" for k, v in hybrid_result.severity_probabilities.items()
                )
                evidence.append(f"Severity probabilities: {probs_str}")

            rules_fired = ["hybrid_pipeline:severity_estimation"]
            if hybrid_result.attention_map is not None:
                rules_fired.append("xai:attention_map_generated")

            return SeverityEstimation(
                label=hybrid_result.severity_label,
                score=hybrid_result.severity_score,
                evidence=evidence,
                rules_fired=rules_fired,
                model_name="hybrid-vision-pipeline",
            )

        try:
            from app.models_ml.severity.estimator import ONNXSeverityEstimator

            estimator = ONNXSeverityEstimator()
            sev = estimator.predict(crop.label, disease.label, image_path)
            return SeverityEstimation.from_xai(sev)
        except Exception:
            pass

        xai_sev = self.baseline.predict(crop.label, disease.label, image_path)
        return SeverityEstimation.from_xai(xai_sev)
