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

    def send(self, user: User, message: str, farm_id: int | None = None, crop_id: int | None = None, input_type: str = "text"):
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
                return self._generate_with_llm(llm, message, context)
            except Exception:
                logger.warning("LLM chat generation failed, falling back to rule-based", exc_info=True)

        return self._generate_rule_based(message, context)

    def _generate_with_llm(self, llm, message: str, context) -> str:
        from app.llm.prompts import CHAT_SYSTEM, CHAT_USER_WITH_CONTEXT

        crop_data = context.crop if hasattr(context, 'crop') else context.get("crop")
        crop_name = crop_data.get("crop_type", "unknown") if crop_data else "unknown"

        location = context.location if hasattr(context, 'location') else context.get("location", "unknown")
        weather = context.weather if hasattr(context, 'weather') else context.get("weather", {})
        history = context.history if hasattr(context, 'history') else context.get("history", [])

        weather_str = f"{weather.get('condition', 'N/A')}, {weather.get('temperature_c', 'N/A')}C, {weather.get('humidity_percent', 'N/A')}% humidity" if isinstance(weather, dict) else str(weather)
        history_str = "\n".join(
            f"- {h.get('crop', '')}: {h.get('disease', '')} ({h.get('severity', '')})"
            for h in history[:5]
        ) if history else "No recent history"

        user_prompt = CHAT_USER_WITH_CONTEXT.format(
            question=message,
            crop=crop_name,
            location=location or "unknown",
            weather_condition=weather.get("condition", "N/A") if isinstance(weather, dict) else "N/A",
            temperature=weather.get("temperature_c", "N/A") if isinstance(weather, dict) else "N/A",
            humidity=weather.get("humidity_percent", "N/A") if isinstance(weather, dict) else "N/A",
            recent_history=history_str,
        )

        response = llm.complete(
            system_prompt=CHAT_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1024,
        )

        if response and len(response.strip()) > 10:
            return response.strip()

        return self._generate_rule_based(message, context)

    def _generate_rule_based(self, message: str, context) -> str:
        crop_data = context.crop if hasattr(context, 'crop') else context.get("crop")
        crop_name = crop_data.get("crop_type", "your crop") if crop_data else "your crop"
        weather = context.weather if hasattr(context, 'weather') else context.get("weather", {})
        history = context.history if hasattr(context, 'history') else context.get("history", [])

        lower = message.lower()
        disease = "possible nutrient stress"
        severity = "low"
        if any(term in lower for term in ["spot", "blast", "fungus", "disease", "yellow", "leaf"]):
            disease = "suspected leaf disease"
            severity = "moderate"
        elif any(term in lower for term in ["pest", "insect", "bug", "worm"]):
            disease = "suspected pest infestation"
            severity = "moderate"

        recommendation = self.engine.generate(
            {"label": crop_name},
            {"label": disease},
            {"label": severity},
            weather if isinstance(weather, dict) else {},
            history if isinstance(history, list) else [],
        )

        return (
            f"For {crop_name}, I see {disease}. {recommendation['action']} "
            f"{recommendation['weather_constraints'][0] if recommendation.get('weather_constraints') else ''}"
        )
