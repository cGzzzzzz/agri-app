from pathlib import Path

from app.models_ml.disease.base import BaseDiseaseModel


class TomatoDiseaseModel(BaseDiseaseModel):
    def __init__(self):
        super().__init__(
            crop="Tomato",
            class_names=["Healthy", "Early Blight", "Late Blight", "Leaf Curl", "Septoria Leaf Spot"],
            model_name="tomato_disease_v1",
        )

    def _get_artifact_path(self) -> Path | None:
        from app.config import get_settings
        settings = get_settings()
        return settings.model_artifacts_dir / "tomato_disease_v1" / "model.onnx"

    def _load_session(self) -> bool:
        return self._try_load_session() is not None
