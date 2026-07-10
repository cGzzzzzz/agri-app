from pathlib import Path

from app.models_ml.disease.base import BaseDiseaseModel


class RiceDiseaseModel(BaseDiseaseModel):
    def __init__(self):
        super().__init__(
            crop="Rice",
            class_names=["Healthy", "Rice Blast", "Brown Spot", "Bacterial Blight", "Sheath Blight"],
            model_name="rice_disease_v1",
        )

    def _get_artifact_path(self) -> Path | None:
        from app.config import get_settings
        settings = get_settings()
        return settings.model_artifacts_dir / "rice_disease_v1" / "model.onnx"

    def _load_session(self) -> bool:
        return self._try_load_session() is not None
