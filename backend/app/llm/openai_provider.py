import json
import logging

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "openai"

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
                msg_list = messages
            else:
                msg_list = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            response = client.chat.completions.create(
                model=self._model,
                messages=msg_list,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception:
            logger.error("OpenAI completion failed", exc_info=True)
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
                f"Respond ONLY with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
            )
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": structured_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            logger.error("OpenAI structured completion failed", exc_info=True)
            return {}
