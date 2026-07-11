from pathlib import Path

from app.models_ml.disease.base import BaseDiseaseModel


class PotatoDiseaseModel(BaseDiseaseModel):
    def __init__(self):
        super().__init__(
            crop="Potato",
            class_names=["Early Blight", "Late Blight", "Healthy"],
            model_name="Potato_disease_model",
        )

    def _get_artifact_path(self) -> Path | None:
        from app.config import get_settings

        settings = get_settings()
        return settings.model_artifacts_dir / "Potato_disease_model" / "1.0.0" / "model.onnx"

    def _load_session(self) -> bool:
        return self._try_load_session() is not None
