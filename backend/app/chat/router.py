from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.chat.service import ChatService
from app.database import get_db
from app.models import User
from app.repositories.history_repository import ConversationRepository
from app.schemas.chat import ChatRead, ChatRequest, ChatResponse
from app.schemas.common import ok

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation, context = ChatService(db).send(
        current_user, payload.message, payload.farm_id, payload.crop_id, payload.input_type
    )
    context_dict = (
        {
            "user": context.user,
            "farm": context.farm,
            "crop": context.crop,
            "weather": context.weather,
            "history": context.history,
            "location": context.location,
        }
        if hasattr(context, "user")
        else context
    )
    data = ChatResponse(
        response=conversation.response,
        conversation=ChatRead.model_validate(conversation),
        context=context_dict,
    )
    return ok(data, "Message processed")


@router.get("/history")
def history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversations = ConversationRepository(db).recent_for_user(current_user.id)
    return ok(
        [ChatRead.model_validate(item) for item in conversations], "Conversation history loaded"
    )
