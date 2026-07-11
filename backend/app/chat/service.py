import json
import logging

from sqlalchemy.orm import Session

from app.models import Conversation, User
from app.orchestrator.context_builder import ContextBuilder
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


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

    def send(
        self,
        user: User,
        message: str,
        farm_id: int | None = None,
        crop_id: int | None = None,
        input_type: str = "text",
    ):
        context = self.context_builder.build(user, farm_id, crop_id)

        response = self._generate_response(user, message, context)

        conversation = Conversation(
            user_id=user.id,
            farm_id=farm_id,
            crop_id=crop_id,
            input_type=input_type,
            question=message,
            response=response,
            context_snapshot=json.dumps(context, default=str),
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation, context

    def _generate_response(self, user: User, message: str, context) -> str:
        llm = self._get_llm()

        if llm and llm.is_available:
            try:
                return self._generate_with_llm(llm, user, message, context)
            except Exception:
                logger.warning(
                    "LLM chat generation failed, falling back to rule-based", exc_info=True
                )

        return self._generate_rule_based(message, context)

    def _generate_with_llm(self, llm, user: User, message: str, context) -> str:
        from app.chat.context_manager import ChatContextManager
        from app.llm.prompts import CHAT_SYSTEM

        ctx_mgr = ChatContextManager(self.db)
        chat_ctx = ctx_mgr.build(
            user_id=user.id,
            system_prompt=CHAT_SYSTEM,
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
            system_prompt=CHAT_SYSTEM,
            user_prompt=message,
            messages=chat_ctx.messages,
            temperature=0.7,
            max_tokens=1024,
        )

        if response and len(response.strip()) > 10:
            return response.strip()

        return self._generate_rule_based(message, context)

    def _generate_rule_based(self, message: str, context) -> str:
        crop_data = context.crop if hasattr(context, "crop") else context.get("crop")
        crop_name = crop_data.get("crop_type", "your crop") if crop_data else "your crop"
        weather = context.weather if hasattr(context, "weather") else context.get("weather", {})

        lower = message.lower()
        if any(term in lower for term in ["weather", "rain", "temperature", "humidity"]):
            if isinstance(weather, dict) and weather.get("status") == "available":
                return (
                    f"Current conditions for {weather.get('location') or 'the selected farm'}: "
                    f"{weather.get('condition')}, {weather.get('temperature_c')}C, "
                    f"humidity {weather.get('humidity_percent')}%. {weather.get('advisory', '')}"
                )
            return "Weather data is not currently available for the selected farm. Configure a provider or verify the farm location."

        return (
            f"I can use the recorded context for {crop_name}, but I cannot diagnose disease from text alone. "
            "Upload a clear leaf image for the trained vision pipeline, or request agronomist review."
        )
