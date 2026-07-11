import json
import logging

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self._api_key)
                self._client = genai.GenerativeModel(self._model)
            except ImportError:
                logger.error("google-generativeai not installed")
                raise
        return self._client

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        try:
            client = self._get_client()
            if messages:
                parts = []
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "system":
                        parts.append(f"[System] {content}")
                    elif role == "assistant":
                        parts.append(f"[Assistant] {content}")
                    else:
                        parts.append(content)
                full_prompt = "\n\n".join(parts)
            else:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            return response.text or ""
        except Exception:
            logger.error("Gemini completion failed", exc_info=True)
            return ""

    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict:
        try:
            client = self._get_client()
            structured_prompt = (
                f"{system_prompt}\n\n"
                f"Respond ONLY with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}\n\n"
                f"{user_prompt}"
            )
            response = client.generate_content(
                structured_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            text = response.text or "{}"
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
            return json.loads(text.strip())
        except Exception:
            logger.error("Gemini structured completion failed", exc_info=True)
            return {}
