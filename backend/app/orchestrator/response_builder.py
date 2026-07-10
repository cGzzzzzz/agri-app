import logging

from app.llm.prompts import RESPONSE_GENERATION_SYSTEM, RESPONSE_GENERATION_USER

logger = logging.getLogger(__name__)


class ResponseBuilder:
    def __init__(self, llm_provider=None):
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

    def generate(self, recommendation: dict) -> str:
        llm = self._get_llm()

        if llm and llm.is_available:
            try:
                return self._generate_with_llm(llm, recommendation)
            except Exception:
                logger.warning("LLM response generation failed, falling back to rule-based", exc_info=True)

        return self._generate_rule_based(recommendation)

    def _generate_with_llm(self, llm, recommendation: dict) -> str:
        user_prompt = RESPONSE_GENERATION_USER.format(
            title=recommendation.get("title", ""),
            action=recommendation.get("action", ""),
            urgency=recommendation.get("urgency", "medium"),
            safety_notes=", ".join(recommendation.get("safety_notes", [])),
            next_steps=", ".join(recommendation.get("next_steps", [])),
            weather_constraints=", ".join(recommendation.get("weather_constraints", [])),
        )

        response = llm.complete(
            system_prompt=RESPONSE_GENERATION_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=512,
        )

        if response and len(response.strip()) > 20:
            return response.strip()

        return self._generate_rule_based(recommendation)

    def _generate_rule_based(self, recommendation: dict) -> str:
        next_step = recommendation.get("next_steps", ["Keep monitoring the crop."])[0] if recommendation.get("next_steps") else "Keep monitoring the crop."
        weather_note = recommendation.get("weather_constraints", [""])[0] if recommendation.get("weather_constraints") else ""
        return (
            f"{recommendation.get('title', '')}. {recommendation.get('action', '')} "
            f"Urgency: {recommendation.get('urgency', 'medium')}. {weather_note} Next: {next_step}"
        ).strip()
