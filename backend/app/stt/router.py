import logging

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.common import ok
from app.stt.service import SttService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stt", tags=["stt"])


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    sample_rate: int = Form(default=48000),
    channels: int = Form(default=1),
):
    audio_bytes = await file.read()
    if not audio_bytes:
        return {"success": False, "message": "Empty audio file", "data": None}

    filename = file.filename or "audio.wav"
    text = SttService().transcribe(
        audio_bytes,
        filename,
        language=language,
        sample_rate=sample_rate,
        channels=channels,
    )
    return ok({"text": text}, "Transcribed successfully")
