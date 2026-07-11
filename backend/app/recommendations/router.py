import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Recommendation, User
from app.orchestrator.context_builder import ContextBuilder
from app.repositories.history_repository import RecommendationRepository
from app.schemas.common import ok
from app.schemas.recommendation import (
    RecommendationPayload,
    RecommendationRead,
    RecommendationRequest,
)
from app.services.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("")
def generate(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    context = ContextBuilder(db).build(current_user, payload.farm_id, payload.crop_id)
    recommendation_payload = RecommendationEngine().generate(
        {"label": payload.crop},
        {"label": payload.disease or "general crop care"},
        {"label": payload.severity or "low"},
        context.weather,
        context.history,
    )
    recommendation = Recommendation(
        user_id=current_user.id,
        farm_id=payload.farm_id,
        crop_id=payload.crop_id,
        title=recommendation_payload["title"],
        action=recommendation_payload["action"],
        urgency=recommendation_payload["urgency"],
        rationale=recommendation_payload["rationale"],
        safety_notes=json.dumps(recommendation_payload["safety_notes"]),
        weather_constraints=json.dumps(recommendation_payload["weather_constraints"]),
        structured_payload=json.dumps(recommendation_payload),
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return ok(RecommendationPayload(**recommendation_payload), "Recommendation generated")


@router.get("/history")
def history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    records = RecommendationRepository(db).recent_for_user(current_user.id)
    return ok(
        [RecommendationRead.model_validate(record) for record in records],
        "Recommendation history loaded",
    )
