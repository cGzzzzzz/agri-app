from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class RecommendationRequest(BaseModel):
    crop: str
    disease: str | None = None
    severity: str | None = None
    farm_id: int | None = None
    crop_id: int | None = None


class RecommendationPayload(BaseModel):
    title: str
    action: str
    urgency: str
    rationale: str
    safety_notes: list[str]
    weather_constraints: list[str]
    next_steps: list[str]
    xai: dict


class RecommendationRead(ORMModel):
    id: int
    user_id: int
    farm_id: int | None
    crop_id: int | None
    prediction_id: int | None
    title: str
    action: str
    urgency: str
    rationale: str
    safety_notes: str | None
    weather_constraints: str | None
    structured_payload: str
    created_at: datetime
