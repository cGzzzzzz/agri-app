from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ChatRequest(BaseModel):
    message: str
    farm_id: int | None = None
    crop_id: int | None = None
    input_type: str = "text"


class ChatRead(ORMModel):
    id: int
    user_id: int
    farm_id: int | None
    crop_id: int | None
    input_type: str
    question: str
    response: str
    created_at: datetime


class ChatResponse(BaseModel):
    response: str
    conversation: ChatRead
    context: dict
