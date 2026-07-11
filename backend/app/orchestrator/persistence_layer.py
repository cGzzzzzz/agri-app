import json

from sqlalchemy.orm import Session

from app.models import Prediction, Recommendation
from app.orchestrator.input_types import (
    CropPrediction,
    DiseasePrediction,
    OrchestratorInput,
    SeverityEstimation,
)
from app.schemas.recommendation import RecommendationPayload


class PersistenceLayer:
    def __init__(self, db: Session):
        self.db = db

    def save(
        self,
        input_data: OrchestratorInput,
        crop: CropPrediction,
        disease: DiseasePrediction,
        severity: SeverityEstimation,
        recommendation_payload: RecommendationPayload,
        response: str,
        trace: list[dict],
    ) -> tuple[Prediction, Recommendation]:
        xai_summary = json.dumps(
            {
                "crop": crop.evidence,
                "disease": disease.evidence,
                "severity": severity.evidence,
                "rules_fired": crop.rules_fired + disease.rules_fired + severity.rules_fired,
            }
        )

        prediction = Prediction(
            user_id=input_data.user_id,
            farm_id=input_data.farm_id,
            crop_id=input_data.crop_id,
            image_id=input_data.image_id,
            crop_name=crop.label,
            crop_confidence=crop.confidence,
            disease_name=disease.label,
            disease_confidence=disease.confidence,
            severity_label=severity.label,
            severity_score=severity.score,
            xai_summary=xai_summary,
            model_trace=json.dumps(trace, default=str),
        )
        self.db.add(prediction)
        self.db.flush()

        rec_payload = (
            recommendation_payload.model_dump()
            if hasattr(recommendation_payload, "model_dump")
            else recommendation_payload
        )

        recommendation = Recommendation(
            user_id=input_data.user_id,
            farm_id=input_data.farm_id,
            crop_id=input_data.crop_id,
            prediction_id=prediction.id,
            title=rec_payload["title"],
            action=rec_payload["action"],
            urgency=rec_payload["urgency"],
            rationale=rec_payload["rationale"],
            safety_notes=json.dumps(rec_payload.get("safety_notes", [])),
            weather_constraints=json.dumps(rec_payload.get("weather_constraints", [])),
            structured_payload=json.dumps(rec_payload),
        )
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(prediction)

        return prediction, recommendation
