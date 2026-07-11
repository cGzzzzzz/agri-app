from pathlib import Path

from app.models_ml.disease.base import BaseDiseaseModel


class BananaDiseaseModel(BaseDiseaseModel):
    def __init__(self):
        super().__init__(
            crop="Banana",
            class_names=["Healthy", "Panama Disease", "Black Sigatoka", "Banana Bunchy Top"],
            model_name="banana_disease_v1",
        )

    def _get_artifact_path(self) -> Path | None:
        from app.config import get_settings

        settings = get_settings()
        return settings.model_artifacts_dir / "banana_disease_v1" / "model.onnx"

    def _load_session(self) -> bool:
        return self._try_load_session() is not None
