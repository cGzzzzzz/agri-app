import json
import logging

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self._api_key,
                base_url="https://api.deepseek.com/v1",
            )
        return self._client

    @property
    def provider_name(self) -> str:
        return "deepseek"

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
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 429:
                logger.warning("DeepSeek 429 rate limit hit")
            else:
                logger.error("DeepSeek completion failed", exc_info=True)
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
                    {"role": "user", "content": "Generate JSON"},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 429:
                logger.warning("DeepSeek 429 rate limit hit (structured)")
            else:
                logger.error("DeepSeek structured completion failed", exc_info=True)
            return {}
