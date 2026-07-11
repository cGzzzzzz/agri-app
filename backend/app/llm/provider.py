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


class FallbackLLMProvider(LLMProvider):
    def __init__(self, providers: list[LLMProvider]):
        self._providers = [p for p in providers if p.is_available]
        self._last_used = None

    @property
    def provider_name(self) -> str:
        if self._last_used:
            return self._last_used.provider_name
        return self._providers[0].provider_name if self._providers else "none"

    @property
    def is_available(self) -> bool:
        return bool(self._providers)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        for provider in self._providers:
            try:
                result = provider.complete(
                    system_prompt, user_prompt, messages, temperature, max_tokens
                )
                if result:
                    self._last_used = provider
                    return result
                logger.warning("Provider %s returned empty — trying next", provider.provider_name)
            except Exception:
                logger.warning("Provider %s failed — trying next", provider.provider_name, exc_info=True)
        logger.error("All LLM providers failed or returned empty")
        return ""

    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict:
        for provider in self._providers:
            try:
                result = provider.complete_structured(
                    system_prompt, user_prompt, schema, temperature, max_tokens
                )
                if result:
                    self._last_used = provider
                    return result
                logger.warning("Provider %s returned empty structured — trying next", provider.provider_name)
            except Exception:
                logger.warning("Provider %s failed structured — trying next", provider.provider_name, exc_info=True)
        logger.error("All LLM providers failed or returned empty (structured)")
        return {}


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    providers: list[LLMProvider] = []

    if settings.nvidia_api_key:
        try:
            from app.llm.nvidia_provider import NvidiaProvider

            providers.append(NvidiaProvider(api_key=settings.nvidia_api_key, model=settings.nvidia_model))
        except Exception:
            logger.warning("Failed to initialize NVIDIA NIM provider", exc_info=True)

    if settings.groq_api_key:
        try:
            from app.llm.groq_provider import GroqProvider

            providers.append(GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model))
        except Exception:
            logger.warning("Failed to initialize Groq provider", exc_info=True)

    if settings.deepseek_api_key:
        try:
            from app.llm.deepseek_provider import DeepSeekProvider

            providers.append(DeepSeekProvider(api_key=settings.deepseek_api_key, model=settings.deepseek_model))
        except Exception:
            logger.warning("Failed to initialize DeepSeek provider", exc_info=True)

    if settings.gemini_api_key:
        try:
            from app.llm.gemini_provider import GeminiProvider

            providers.append(GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model))
        except Exception:
            logger.warning("Failed to initialize Gemini provider", exc_info=True)

    if settings.openai_api_key:
        try:
            from app.llm.openai_provider import OpenAIProvider

            providers.append(OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model))
        except Exception:
            logger.warning("Failed to initialize OpenAI provider", exc_info=True)

    if providers:
        if len(providers) == 1:
            return providers[0]
        logger.info("LLM fallback chain: %s", " → ".join(p.provider_name for p in providers))
        return FallbackLLMProvider(providers)

    return NullLLMProvider()
