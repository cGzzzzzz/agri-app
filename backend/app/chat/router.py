from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.chat.service import ChatService
from app.database import get_db
from app.models import Conversation, User
from app.repositories.history_repository import ConversationRepository
from app.schemas.chat import ChatAccepted, ChatRead, ChatRequest, ChatStatusResponse
from app.schemas.common import ok

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def send_message(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation, _ = ChatService(db).create_pending(
        current_user,
        payload.message,
        payload.farm_id,
        payload.crop_id,
        payload.input_type,
        payload.response_language,
    )
    background_tasks.add_task(ChatService.generate_and_persist, conversation.id)
    return ok(
        ChatAccepted(message_id=conversation.id, status=conversation.status), "Message accepted"
    )


@router.get("/status/{message_id}")
def message_status(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = db.get(Conversation, message_id)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat message not found")
    return ok(
        ChatStatusResponse(
            message_id=conversation.id,
            status=conversation.status,
            response=conversation.response if conversation.status == "completed" else None,
            error_message=conversation.error_message,
        ),
        "Chat message status loaded",
    )


@router.get("/history")
def history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversations = ConversationRepository(db).recent_for_user(current_user.id)
    return ok(
        [ChatRead.model_validate(item) for item in conversations], "Conversation history loaded"
    )
