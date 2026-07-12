import logging

from app.config import get_settings
from app.vision.types import VisionModelCard

logger = logging.getLogger(__name__)


class VisionModelRegistry:
    def __init__(self):
        self._trained_cards: list[VisionModelCard] = []

    def _ensure_loaded(self) -> None:
        if self._trained_cards:
            return
        try:
            from app.models_ml.registry.model_registry import ModelRegistry

            settings = get_settings()
            registry = ModelRegistry(settings.model_artifacts_dir)
            registry.discover()

            for meta in registry.list_models():
                card = VisionModelCard(
                    name=meta.name,
                    task=meta.task,
                    version=meta.version,
                    backend=meta.framework,
                    status="trained",
                    labels=meta.classes,
                    explainability=["gradcam", "integrated_gradients", "evidence", "rules_fired"],
                    upgrade_path="",
                    framework=meta.framework,
                    crop=meta.crop,
                    classes=meta.classes,
                    input_shape=meta.input_shape,
                    metrics=meta.metrics,
                )
                self._trained_cards.append(card)
        except Exception:
            logger.debug("Could not load trained models from registry", exc_info=True)

    def active_cards(self) -> list[VisionModelCard]:
        self._ensure_loaded()
        return list(self._trained_cards)

    def has_trained_model(self, task: str, crop: str = "") -> bool:
        self._ensure_loaded()
        for card in self._trained_cards:
            if card.task == task and (not crop or card.crop.lower() == crop.lower()):
                return True
        return False
