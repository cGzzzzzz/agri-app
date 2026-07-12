import logging

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.chat.service import ChatService
from app.config import get_settings
from app.crops.router import router as crops_router
from app.database import get_db
from app.disease.router import router as disease_router
from app.farms.router import router as farms_router
from app.models import Crop, Farm, User
from app.orchestrator.hierarchical_orchestrator import HierarchicalAgriculturalOrchestrator
from app.recommendations.router import router as recommendations_router
from app.schemas.common import ok
from app.services.storage import LocalFileStorage
from app.stt.router import router as stt_router
from app.users.router import router as users_router
from app.weather.router import router as weather_router
from app.weather.service import WeatherService

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Modular monolith backend for an explainable AI agriculture platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again later."},
    )


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(farms_router, prefix=settings.api_prefix)
app.include_router(crops_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(disease_router, prefix=settings.api_prefix)
app.include_router(recommendations_router, prefix=settings.api_prefix)
app.include_router(weather_router, prefix=settings.api_prefix)
app.include_router(stt_router, prefix=settings.api_prefix)


@app.on_event("startup")
def ensure_local_storage() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.model_artifacts_dir.mkdir(parents=True, exist_ok=True)

    try:
        from app.models_ml.registry.model_registry import ModelRegistry

        registry = ModelRegistry(settings.model_artifacts_dir)
        count = registry.discover()
        logger.info("Model registry startup: %d trained models discovered", count)
        app.state.model_registry = registry
    except Exception:
        logger.warning("Model registry discovery failed at startup", exc_info=True)
        app.state.model_registry = None

    try:
        from app.llm.provider import get_llm_provider

        llm = get_llm_provider()
        app.state.llm_provider = llm
        logger.info(
            "LLM provider initialized: %s (available=%s)", llm.provider_name, llm.is_available
        )
    except Exception:
        logger.warning("LLM provider initialization failed", exc_info=True)
        app.state.llm_provider = None

    if settings.rag_enabled:
        try:
            from app.rag.embeddings import get_embedding_provider
            from app.rag.knowledge_base import KnowledgeBase
            from app.rag.vector_store import InMemoryVectorStore

            embedding_provider = get_embedding_provider(api_key=settings.openai_api_key)
            vector_store = InMemoryVectorStore()
            kb = KnowledgeBase(
                vector_store,
                embedding_provider,
                settings.model_artifacts_dir.parent / "app" / "rag" / "documents",
            )
            ingested = kb.ingest_directory()
            app.state.knowledge_base = kb
            logger.info("RAG knowledge base initialized: %d documents ingested", ingested)
        except Exception:
            logger.warning("RAG knowledge base initialization failed", exc_info=True)
            app.state.knowledge_base = None
    else:
        app.state.knowledge_base = None


@app.get("/")
def root():
    return ok({"name": settings.app_name, "version": settings.app_version}, "AgriAI API is running")


def _get_user_farm_and_crop(db: Session, user: User) -> tuple[Farm, Crop]:
    farm = db.query(Farm).filter(Farm.user_id == user.id).first()
    if farm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create a farm before using this endpoint.",
        )
    crop = db.query(Crop).filter(Crop.farm_id == farm.id).first()
    if crop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create a crop before using this endpoint.",
        )
    return farm, crop


@app.get("/api/weather")
def get_weather():
    weather = WeatherService().current()
    temperature = weather.get("temperature_c")
    humidity = weather.get("humidity_percent")
    precipitation = weather.get("precipitation_probability_percent")
    return {
        "temperature": f"{temperature:.0f} C" if temperature is not None else "unavailable",
        "condition": weather.get("condition", "unavailable"),
        "description": weather.get("advisory", "Weather data unavailable."),
        "precipitation_probability": f"{precipitation}%"
        if precipitation is not None
        else "unavailable",
        "humidity": f"{humidity}%" if humidity is not None else "unavailable",
        "status": weather.get("status", "available"),
    }


@app.get("/api/crop")
def get_crop(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _, crop = _get_user_farm_and_crop(db, user)
    return {
        "crop_type": crop.crop_type,
        "crop_variety": crop.crop_variety or "",
        "sowing_date": crop.sowing_date.isoformat() if crop.sowing_date else "",
        "field_size": crop.field_size or "",
    }


@app.post("/api/crop")
def update_crop(
    payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    farm, crop = _get_user_farm_and_crop(db, user)
    crop.farm_id = farm.id
    crop.crop_type = payload.get("crop_type", crop.crop_type)
    crop.crop_variety = payload.get("crop_variety", crop.crop_variety)
    crop.field_size = payload.get("field_size", crop.field_size)
    db.commit()
    db.refresh(crop)
    return {"status": "success", "crop": get_crop(db, user)}


@app.post("/api/chat", status_code=status.HTTP_202_ACCEPTED)
def send_chat(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    farm, crop = _get_user_farm_and_crop(db, user)
    conversation, _ = ChatService(db).create_pending(
        user, payload.get("message", ""), farm.id, crop.id
    )
    background_tasks.add_task(ChatService.generate_and_persist, conversation.id)
    return {"message_id": conversation.id, "status": conversation.status}


@app.post("/api/scan")
async def scan_image(
    file: UploadFile = File(...),
    farm_id: int | None = Form(default=None),
    crop: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    farm, crop_obj = _get_user_farm_and_crop(db, user)
    target_farm_id = farm_id or farm.id
    image = await LocalFileStorage().save_image(db, user.id, file, target_farm_id)
    result = HierarchicalAgriculturalOrchestrator(db).analyze_image(
        user, image.storage_path, image.id, target_farm_id, crop_obj.id, crop_override=crop
    )
    return {
        "disease": f"{result.disease.label} ({int(result.disease.confidence * 100)}%)",
        "confidence": f"{int(result.disease.confidence * 100)}%",
        "severity": result.severity.label.upper(),
        "recommendation": result.response,
        "xai": {
            "evidence": result.disease.evidence,
            "rules_fired": result.disease.rules_fired,
            "trace": result.trace,
        },
    }
