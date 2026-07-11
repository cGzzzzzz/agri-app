import logging
from pathlib import Path

import numpy as np

from app.models_ml.errors import ModelUnavailableError
from app.orchestrator.input_types import CropPrediction, DiseasePrediction, SeverityEstimation

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
    def detect(self, state: dict) -> DiseasePrediction:
        crop: CropPrediction = state["crop_resolution"]
        image_path = Path(state["input"].image_path)

        if crop.status != "available":
            return DiseasePrediction(
                label="model_unavailable",
                confidence=0.0,
                evidence=[
                    "Disease detection requires a resolved crop or a trained crop classifier."
                ],
                rules_fired=["orchestrator:crop_resolution_unavailable"],
                heatmap_hint=None,
                model_name="",
                status="unavailable",
                unavailable_reason=crop.unavailable_reason,
            )

        try:
            from app.models_ml.disease.registry import DiseaseModelRegistry

            onnx_pred = DiseaseModelRegistry.predict(crop.label, image_path)
            if onnx_pred is None:
                raise ModelUnavailableError("disease_classification", crop.label)
            return DiseasePrediction.from_xai(onnx_pred)
        except Exception as exc:
            logger.exception("Disease prediction unavailable for crop=%s", crop.label)
            return DiseasePrediction(
                label="model_unavailable",
                confidence=0.0,
                evidence=[f"No usable trained disease model is available for {crop.label}."],
                rules_fired=["model_registry:disease_model_unavailable"],
                heatmap_hint=None,
                model_name="",
                status="unavailable",
                unavailable_reason=str(exc),
            )


class SeverityEstimatorStage:
    def estimate(self, state: dict) -> SeverityEstimation:
        crop: CropPrediction = state["crop_resolution"]
        disease: DiseasePrediction = state["disease_detection"]
        image_path = Path(state["input"].image_path)

        if disease.status != "available":
            return SeverityEstimation(
                label="model_unavailable",
                score=0.0,
                evidence=["Severity cannot be estimated without a disease prediction."],
                rules_fired=["orchestrator:disease_detection_unavailable"],
                model_name="",
                status="unavailable",
                unavailable_reason=disease.unavailable_reason,
            )
        try:
            from app.models_ml.severity.estimator import ONNXSeverityEstimator

            estimator = ONNXSeverityEstimator()
            sev = estimator.predict(crop.label, disease.label, image_path)
            return SeverityEstimation.from_xai(sev)
        except Exception as exc:
            logger.exception("Severity prediction unavailable")
            return SeverityEstimation(
                label="model_unavailable",
                score=0.0,
                evidence=["No usable trained severity model is available."],
                rules_fired=["model_registry:severity_model_unavailable"],
                model_name="",
                status="unavailable",
                unavailable_reason=str(exc),
            )
