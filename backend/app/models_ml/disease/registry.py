import logging
from pathlib import Path

from app.models_ml.disease.base import BaseDiseaseModel
from app.models_ml.disease.pepper import PepperDiseaseModel
from app.models_ml.disease.potato import PotatoDiseaseModel
from app.models_ml.disease.rice import RiceDiseaseModel
from app.models_ml.disease.tomato import TomatoDiseaseModel
from app.vision.types import XAIPrediction

logger = logging.getLogger(__name__)


class DiseaseModelRegistry:
    _crop_models: dict[str, type[BaseDiseaseModel]] = {
        "rice": RiceDiseaseModel,
        "tomato": TomatoDiseaseModel,
        "potato": PotatoDiseaseModel,
        "pepper": PepperDiseaseModel,
    }

    @classmethod
    def get_model(cls, crop: str) -> BaseDiseaseModel | None:
        model_cls = cls._crop_models.get(crop.lower())
        if model_cls:
            return model_cls()
        return None

    @classmethod
    def predict(cls, crop: str, image: Path) -> XAIPrediction | None:
        model = cls.get_model(crop)
        if model is None:
            return None
        return model.predict(image)

    @classmethod
    def supported_crops(cls) -> list[str]:
        return list(cls._crop_models.keys())

    @classmethod
    def register_crop(cls, crop: str, model_cls: type[BaseDiseaseModel]) -> None:
        cls._crop_models[crop.lower()] = model_cls

    @classmethod
    def get_classes(cls, crop: str) -> list[str]:
        model = cls.get_model(crop)
        return model.class_names if model else []
