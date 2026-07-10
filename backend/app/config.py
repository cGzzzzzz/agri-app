from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgriAI Backend"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    environment: str = "local"

    database_url: str = "sqlite:///./agri_ai.db"
    secret_key: str = Field(default="change-this-local-secret")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 30

    storage_dir: Path = Path("storage")
    cors_origins: str = "*"

    # Model / ML
    model_artifacts_dir: Path = Path("artifacts")
    onnx_threads: int = 4
    image_target_width: int = 224
    image_target_height: int = 224
    image_max_size_mb: float = 20.0
    device: str = "cpu"  # "cpu" | "cuda" | "mps"
    yolo_model_size: str = "n"  # n=nano, s=small, m=medium
    classification_backbone: str = "efficientnet_b0"

    # XAI
    gradcam_enabled: bool = True
    xai_detail_level: str = "full"  # "full" | "farmer" | "analyst"
    uncertainty_mc_samples: int = 10

    # LLM
    llm_provider: str = "none"  # "none" | "openai" | "gemini"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Weather
    weather_provider: str = "local"  # "local" | "openmeteo"

    # RAG
    rag_enabled: bool = False
    rag_top_k: int = 5
    rag_score_threshold: float = 0.5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
