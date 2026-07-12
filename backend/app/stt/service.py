import logging
import re

import httpx

from app.config import get_settings
from app.stt.audio_processor import preprocess_audio

logger = logging.getLogger(__name__)
settings = get_settings()

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

_HALLUCINATION_PHRASES = re.compile(
    r"(thank you for watching|thanks for watching|thank you so much for watching|"
    r"please subscribe|subscribe to my channel|click the bell|like and subscribe|"
    r"see you in the next video|see you next time|bye bye|"
    r"subtitles by|closed captions|captioning by)",
    re.IGNORECASE,
)

_MIN_AUDIO_BYTES = 1000


class SttService:
    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str = "en",
        sample_rate: int = 48000,
        channels: int = 1,
    ) -> str:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        if len(audio_bytes) < _MIN_AUDIO_BYTES:
            raise ValueError("Audio too short — speak for at least 1 second")

        processed = preprocess_audio(audio_bytes, sample_rate_in=sample_rate, channels=channels)

        content_type = "audio/wav"
        wav_name = filename.rsplit(".", 1)[0] + ".wav" if "." in filename else filename + ".wav"
        files = {"file": (wav_name, processed, content_type)}
        data = {
            "model": "whisper-large-v3",
            "language": language,
            "prompt": "Voice dictation for agricultural advice about crops, diseases, weather, and farming.",
            "temperature": 0,
        }

        try:
            resp = httpx.post(
                GROQ_STT_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files=files,
                data=data,
                timeout=60.0,
            )
            resp.raise_for_status()
            result = resp.json()
            text = result.get("text", "")
            return _filter_hallucinations(text)
        except httpx.HTTPStatusError as e:
            logger.error("Groq STT HTTP error %s: %s", e.response.status_code, e.response.text)
            raise RuntimeError(
                f"STT failed ({e.response.status_code}): {e.response.text[:200]}"
            ) from e
        except ValueError:
            raise
        except Exception as e:
            logger.error("Groq STT error: %s", e)
            raise RuntimeError(f"STT request failed: {e}") from e


def _filter_hallucinations(text: str) -> str:
    cleaned = _HALLUCINATION_PHRASES.sub("", text).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned
