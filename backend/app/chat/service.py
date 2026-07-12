import json
import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Conversation, User
from app.orchestrator.context_builder import ContextBuilder
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class ChatGenerationError(RuntimeError):
    pass


class ChatService:
    def __init__(self, db: Session, llm_provider=None):
        self.db = db
        self.context_builder = ContextBuilder(db)
        self.engine = RecommendationEngine()
        self._llm = llm_provider

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        try:
            from app.llm.provider import get_llm_provider

            self._llm = get_llm_provider()
            return self._llm
        except Exception:
            return None

    def create_pending(
        self,
        user: User,
        message: str,
        farm_id: int | None = None,
        crop_id: int | None = None,
        input_type: str = "text",
        response_language: str = "en",
    ):
        context = self.context_builder.build(user, farm_id, crop_id)
        response_language = (response_language or "en").strip().lower()
        if not response_language:
            response_language = "en"
        context_payload = {
            "context": context,
            "response_language": response_language,
        }

        conversation = Conversation(
            user_id=user.id,
            farm_id=farm_id,
            crop_id=crop_id,
            input_type=input_type,
            question=message,
            response="",
            status="pending",
            context_snapshot=json.dumps(context_payload, default=str),
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation, context

    @classmethod
    def generate_and_persist(cls, conversation_id: int) -> None:
        """Generate with a fresh database session after the HTTP response is sent."""
        db = SessionLocal()
        try:
            conversation = db.get(Conversation, conversation_id)
            if conversation is None or conversation.status == "completed":
                return

            conversation.status = "processing"
            conversation.error_message = None
            db.commit()

            user = db.get(User, conversation.user_id)
            if user is None:
                raise ChatGenerationError("The conversation user no longer exists.")

            service = cls(db)
            context = service.context_builder.build(
                user, conversation.farm_id, conversation.crop_id
            )
            response_language = "en"
            if conversation.context_snapshot:
                try:
                    snapshot = json.loads(conversation.context_snapshot)
                    if isinstance(snapshot, dict):
                        response_language = (
                            str(snapshot.get("response_language", "en")).strip().lower() or "en"
                        )
                except Exception:
                    response_language = "en"

            conversation.response = service._generate_response(
                user, conversation.question, context, response_language
            )
            conversation.status = "completed"
            conversation.error_message = None
            db.commit()
        except Exception as exc:
            logger.exception("Chat generation failed for conversation %s", conversation_id)
            db.rollback()
            conversation = db.get(Conversation, conversation_id)
            if conversation is not None:
                conversation.status = "failed"
                conversation.error_message = str(exc)[:1000]
                db.commit()
        finally:
            db.close()

    def _generate_response(
        self, user: User, message: str, context, response_language: str = "en"
    ) -> str:
        llm = self._get_llm()

        if llm is None or not llm.is_available:
            raise ChatGenerationError("No configured LLM provider is available.")
        return self._generate_with_llm(llm, user, message, context, response_language)

    def _generate_with_llm(
        self, llm, user: User, message: str, context, response_language: str = "en"
    ) -> str:
        from app.chat.context_manager import ChatContextManager
        from app.llm.prompts import CHAT_SYSTEM

        language_instruction = (
            "Respond in English unless the user explicitly changes the assistant language selector. "
            f"The selected response language for this reply is '{response_language}'. "
            "Use that language for the full reply."
        )

        ctx_mgr = ChatContextManager(self.db)
        chat_ctx = ctx_mgr.build(
            user_id=user.id,
            system_prompt=f"{CHAT_SYSTEM}\n\n{language_instruction}",
            current_message=message,
            context={
                "crop": context.crop if hasattr(context, "crop") else context.get("crop"),
                "location": context.location
                if hasattr(context, "location")
                else context.get("location"),
                "weather": context.weather
                if hasattr(context, "weather")
                else context.get("weather"),
                "history": context.history
                if hasattr(context, "history")
                else context.get("history"),
            },
            llm_provider=llm,
        )

        response = llm.complete(
            system_prompt=f"{CHAT_SYSTEM}\n\n{language_instruction}",
            user_prompt=message,
            messages=chat_ctx.messages,
            temperature=0.9,
            max_tokens=1024,
        )

        if response and len(response.strip()) > 10:
            return response.strip()

        raise ChatGenerationError("The LLM returned an empty response.")
