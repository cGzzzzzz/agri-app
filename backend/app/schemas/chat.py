from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ChatRequest(BaseModel):
    message: str
    farm_id: int | None = None
    crop_id: int | None = None
    input_type: str = "text"
    response_language: str = "en"


class ChatRead(ORMModel):
    id: int
    user_id: int
    farm_id: int | None
    crop_id: int | None
    input_type: str
    question: str
    response: str
    status: str
    error_message: str | None = None
    created_at: datetime


class ChatResponse(BaseModel):
    response: str
    conversation: ChatRead
    context: dict


class ChatAccepted(BaseModel):
    message_id: int
    status: str


class ChatStatusResponse(BaseModel):
    message_id: int
    status: str
    response: str | None = None
    error_message: str | None = None
