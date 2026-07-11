import logging
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError


class NullLLMProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "none"

    @property
    def is_available(self) -> bool:
        return False

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        return ""

    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict:
        return {}


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = settings.llm_provider.lower()

    if provider_name == "openai" and settings.openai_api_key:
        try:
            from app.llm.openai_provider import OpenAIProvider

            return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
        except Exception:
            logger.warning("Failed to initialize OpenAI provider", exc_info=True)

    if provider_name == "gemini" and settings.gemini_api_key:
        try:
            from app.llm.gemini_provider import GeminiProvider

            return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        except Exception:
            logger.warning("Failed to initialize Gemini provider", exc_info=True)

    if provider_name == "groq" and settings.groq_api_key:
        try:
            from app.llm.groq_provider import GroqProvider

            return GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model)
        except Exception:
            logger.warning("Failed to initialize Groq provider", exc_info=True)

    return NullLLMProvider()
