import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Prediction, Recommendation, User
from app.orchestrator.context_builder import ContextBuilder
from app.orchestrator.crop_resolver import CropResolver
from app.orchestrator.disease_detector import DiseaseDetector
from app.orchestrator.image_preprocessor_stage import ImagePreprocessorStage
from app.orchestrator.input_types import (
    CropPrediction,
    DiseasePrediction,
    OrchestratorContext,
    OrchestratorInput,
    OrchestratorResult,
    SeverityEstimation,
)
from app.orchestrator.input_validator import InputValidator, ValidationError
from app.orchestrator.persistence_layer import PersistenceLayer
from app.orchestrator.pipeline import Pipeline, PipelineStage
from app.orchestrator.response_builder import ResponseBuilder
from app.orchestrator.severity_estimator import SeverityEstimatorStage
from app.schemas.disease import DiseaseAnalysisRead, PredictorOutput, SeverityOutput, XAIReportOutput
from app.schemas.recommendation import RecommendationPayload
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class XAIReportStage:
    def __init__(self):
        self._report_builder = None

    def _get_report_builder(self):
        if self._report_builder is not None:
            return self._report_builder
        try:
            from app.vision.xai.report_builder import XAIReportBuilder

            settings = get_settings()
            self._report_builder = XAIReportBuilder(
                model=None,
                target_layer=None,
                mc_samples=settings.uncertainty_mc_samples,
            )
            return self._report_builder
        except Exception:
            logger.debug("XAIReportBuilder not available", exc_info=True)
            return None

    def build_report(
        self,
        image_path: str,
        disease_name: str,
        disease_probs: dict[str, float],
        severity_score: float,
        severity_label: str,
        detections: list | None = None,
        weather: dict | None = None,
        model_versions: dict[str, str] | None = None,
    ):
        builder = self._get_report_builder()
        if builder is None:
            return None, None

        try:
            from PIL import Image as PILImage
            import torch

            pil_img = PILImage.open(image_path).convert("RGB")
            img_224 = pil_img.resize((224, 224), PILImage.BILINEAR)
            image_arr = np.array(img_224, dtype=np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            image_arr = (image_arr - mean) / std
            input_tensor = torch.from_numpy(image_arr.transpose(2, 0, 1)).unsqueeze(0)

            img_640 = np.array(pil_img.resize((640, 640), PILImage.BILINEAR))
        except Exception:
            logger.debug("Failed to prepare tensor for XAI report", exc_info=True)
            return None, None

        report = builder.build(
            image=img_640,
            input_tensor=input_tensor,
            detections=detections or [],
            disease_name=disease_name,
            disease_probs=disease_probs,
            severity_score=severity_score,
            severity_label=severity_label,
            weather=weather,
            model_versions=model_versions,
        )
        farmer_view = report.to_farmer_view()

        try:
            xai_output = XAIReportOutput(
                detections=[{"bbox": list(d.bbox), "class_label": d.class_label, "confidence": d.confidence, "area_pixels": d.area_pixels} for d in report.detections],
                lesion_regions=[r.to_dict() for r in report.lesion_regions],
                class_probabilities=report.class_probabilities,
                predicted_class=report.predicted_class,
                confidence=report.confidence,
                gradcam_available=bool(report.gradcam_heatmap),
                attention_map_available=bool(report.attention_map),
                feature_attribution=report.feature_attribution.to_dict(),
                severity=report.severity.to_dict(),
                uncertainty=report.uncertainty.to_dict(),
                model_features=[f.to_dict() for f in report.model_features],
                agronomic=report.agronomic.to_dict(),
                pipeline_trace=report.pipeline_trace,
                model_versions=report.model_versions,
            )
        except Exception:
            xai_output = None

        return xai_output, farmer_view


class HierarchicalAgriculturalOrchestrator:
    def __init__(
        self,
        db: Session,
        validator: InputValidator | None = None,
        context_builder: ContextBuilder | None = None,
        image_preprocessor: ImagePreprocessorStage | None = None,
        crop_resolver: CropResolver | None = None,
        disease_detector: DiseaseDetector | None = None,
        severity_estimator: SeverityEstimatorStage | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        response_builder: ResponseBuilder | None = None,
        persistence: PersistenceLayer | None = None,
    ):
        self.db = db
        self.validator = validator or InputValidator()
        self.context_builder = context_builder or ContextBuilder(db)
        self.image_preprocessor = image_preprocessor or ImagePreprocessorStage()
        self.crop_resolver = crop_resolver or CropResolver()
        self.disease_detector = disease_detector or DiseaseDetector()
        self.severity_estimator = severity_estimator or SeverityEstimatorStage()
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.response_builder = response_builder or ResponseBuilder()
        self.persistence = persistence or PersistenceLayer(db)
        self.xai_stage = XAIReportStage()

    def analyze_image(
        self,
        user: User,
        image_path: str,
        image_id: int | None,
        farm_id: int | None = None,
        crop_id: int | None = None,
        crop_override: str | None = None,
        include_xai_heatmap: bool = False,
    ) -> DiseaseAnalysisRead:
        input_data = self.validator.validate(
            state={},
            user=user,
            image_path=image_path,
            image_id=image_id,
            farm_id=farm_id,
            crop_id=crop_id,
            crop_override=crop_override,
            include_xai_heatmap=include_xai_heatmap,
        )

        context = self.context_builder.build(user, farm_id, crop_id)

        crop = self.crop_resolver.resolve({"input": input_data, "context": context})

        pipeline_state = {
            "input": input_data,
            "context": context,
            "crop_resolution": crop,
        }

        disease = self.disease_detector.detect(pipeline_state)

        pipeline_state["disease_detection"] = disease
        severity = self.severity_estimator.estimate(pipeline_state)

        weather = context.weather
        history = context.history

        xai_report = None
        xai_farmer_view = None
        hybrid_result = pipeline_state.get("_hybrid_result")
        hybrid_detections = hybrid_result.detections if hybrid_result is not None else None

        if include_xai_heatmap:
            xai_report, xai_farmer_view = self.xai_stage.build_report(
                image_path=image_path,
                disease_name=disease.label,
                disease_probs={disease.label: disease.confidence},
                severity_score=severity.score,
                severity_label=severity.label,
                detections=hybrid_detections,
                weather=weather,
            )

        recommendation_payload = self.recommendation_engine.generate(
            asdict(crop) if not isinstance(crop, dict) else crop,
            asdict(disease) if not isinstance(disease, dict) else disease,
            asdict(severity) if not isinstance(severity, dict) else severity,
            weather,
            history,
        )

        response = self.response_builder.generate(recommendation_payload)

        trace: list[dict] = []
        trace.append({"step": "input_validation", "status": "completed", "data": {"image_path": image_path}})
        trace.append({"step": "context_builder", "status": "completed", "data": context.__dict__ if hasattr(context, '__dict__') else context})
        trace.append({"step": "crop_resolution", "status": "completed", "data": asdict(crop)})
        trace.append({"step": "disease_detection", "status": "completed", "data": asdict(disease)})
        trace.append({"step": "severity_estimation", "status": "completed", "data": asdict(severity)})
        trace.append({"step": "weather_context", "status": "completed", "data": weather})
        trace.append({"step": "historical_context", "status": "completed", "data": history})
        trace.append({"step": "recommendation_engine", "status": "completed", "data": recommendation_payload})

        if xai_report is not None:
            trace.append({"step": "xai_report_generation", "status": "completed", "data": {"farmer_view": xai_farmer_view}})
        else:
            trace.append({"step": "xai_report_generation", "status": "skipped", "data": {"reason": "include_xai_heatmap=False or XAI unavailable"}})

        trace.append({"step": "response_builder", "status": "completed", "data": {"response": response}})

        rec_payload = RecommendationPayload(**recommendation_payload)

        prediction, recommendation = self.persistence.save(
            input_data=input_data,
            crop=crop,
            disease=disease,
            severity=severity,
            recommendation_payload=rec_payload,
            response=response,
            trace=trace,
        )

        return DiseaseAnalysisRead(
            prediction_id=prediction.id,
            image_id=image_id,
            crop=PredictorOutput(**asdict(crop)),
            disease=PredictorOutput(
                label=disease.label,
                confidence=disease.confidence,
                evidence=disease.evidence,
                rules_fired=disease.rules_fired,
                heatmap_hint=disease.heatmap_hint,
            ),
            severity=SeverityOutput(**asdict(severity)),
            weather=weather,
            history=history,
            recommendation=rec_payload,
            response=response,
            trace=trace,
            created_at=datetime.utcnow(),
            xai_report=xai_report,
            xai_farmer_view=xai_farmer_view,
        )
