import logging

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.chat.service import ChatService
from app.config import get_settings
from app.crops.router import router as crops_router
from app.database import Base, engine, get_db
from app.disease.router import router as disease_router
from app.farms.router import router as farms_router
from app.models import Crop, Farm, User
from app.orchestrator.hierarchical_orchestrator import HierarchicalAgriculturalOrchestrator
from app.recommendations.router import router as recommendations_router
from app.schemas.common import ok
from app.services.security import hash_password
from app.services.storage import LocalFileStorage
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

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(farms_router, prefix=settings.api_prefix)
app.include_router(crops_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(disease_router, prefix=settings.api_prefix)
app.include_router(recommendations_router, prefix=settings.api_prefix)
app.include_router(weather_router, prefix=settings.api_prefix)


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
        logger.info("LLM provider initialized: %s (available=%s)", llm.provider_name, llm.is_available)
    except Exception:
        logger.warning("LLM provider initialization failed", exc_info=True)
        app.state.llm_provider = None

    if settings.rag_enabled:
        try:
            from app.rag.vector_store import InMemoryVectorStore
            from app.rag.embeddings import get_embedding_provider
            from app.rag.knowledge_base import KnowledgeBase

            embedding_provider = get_embedding_provider(api_key=settings.openai_api_key)
            vector_store = InMemoryVectorStore()
            kb = KnowledgeBase(vector_store, embedding_provider, settings.model_artifacts_dir.parent / "app" / "rag" / "documents")
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


def _compat_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "demo@agriai.local").first()
    if user is None:
        user = User(email="demo@agriai.local", name="Demo Farmer", phone="9999999999", hashed_password=hash_password("password"))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _compat_farm_and_crop(db: Session, user: User) -> tuple[Farm, Crop]:
    farm = db.query(Farm).filter(Farm.user_id == user.id).first()
    if farm is None:
        farm = Farm(user_id=user.id, name="Demo Farm", village="Local", district="Local District", state="Tamil Nadu", area=12.5)
        db.add(farm)
        db.commit()
        db.refresh(farm)
    crop = db.query(Crop).filter(Crop.farm_id == farm.id).first()
    if crop is None:
        crop = Crop(farm_id=farm.id, crop_type="Rice", crop_variety="Basmati Rice", field_size="12.5", growth_stage="Vegetative")
        db.add(crop)
        db.commit()
        db.refresh(crop)
    return farm, crop


@app.get("/api/weather")
def compat_weather():
    weather = WeatherService().current()
    return {
        "temperature": f"{weather['temperature_c']:.0f} C",
        "condition": weather["condition"],
        "description": weather["advisory"],
        "precipitation_probability": f"{weather['precipitation_probability_percent']}%",
        "humidity": f"{weather['humidity_percent']}%",
    }


@app.get("/api/crop")
def compat_get_crop(db: Session = Depends(get_db)):
    user = _compat_user(db)
    _, crop = _compat_farm_and_crop(db, user)
    return {
        "crop_type": crop.crop_type,
        "crop_variety": crop.crop_variety or "",
        "sowing_date": crop.sowing_date.isoformat() if crop.sowing_date else "",
        "field_size": crop.field_size or "",
    }


@app.post("/api/crop")
def compat_register_crop(payload: dict, db: Session = Depends(get_db)):
    user = _compat_user(db)
    farm, crop = _compat_farm_and_crop(db, user)
    crop.farm_id = farm.id
    crop.crop_type = payload.get("crop_type", crop.crop_type)
    crop.crop_variety = payload.get("crop_variety", crop.crop_variety)
    crop.field_size = payload.get("field_size", crop.field_size)
    db.commit()
    db.refresh(crop)
    return {"status": "success", "crop": compat_get_crop(db)}


@app.post("/api/chat")
def compat_chat(payload: dict, db: Session = Depends(get_db)):
    user = _compat_user(db)
    farm, crop = _compat_farm_and_crop(db, user)
    conversation, _ = ChatService(db).send(user, payload.get("message", ""), farm.id, crop.id)
    return {"response": conversation.response}


@app.post("/api/scan")
async def compat_scan(file: UploadFile = File(...), farm_id: int | None = Form(default=None), db: Session = Depends(get_db)):
    user = _compat_user(db)
    farm, crop = _compat_farm_and_crop(db, user)
    target_farm_id = farm_id or farm.id
    image = await LocalFileStorage().save_image(db, user.id, file, target_farm_id)
    result = HierarchicalAgriculturalOrchestrator(db).analyze_image(user, image.storage_path, image.id, target_farm_id, crop.id)
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
