import logging
from pathlib import Path

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

        cards: list[VisionModelCard] = list(self._trained_cards)

        trained_tasks = {c.task for c in cards}
        trained_crops = {c.crop for c in cards if c.crop}

        if "crop_classification" not in trained_tasks:
            cards.append(VisionModelCard(
                name="crop-local-xai-baseline",
                task="crop_classification",
                version="0.1.0",
                backend="rules-and-metadata",
                status="baseline",
                labels=["Rice", "Tomato", "Wheat"],
                explainability=["rules_fired", "evidence", "heatmap_hint"],
                upgrade_path="Replace with ONNX/EfficientNet or ConvNeXt crop classifier trained on project images.",
            ))

        if "disease_detection" not in trained_tasks:
            for crop in ["Rice", "Tomato", "Banana"]:
                if crop.lower() not in {c.lower() for c in trained_crops}:
                    cards.append(VisionModelCard(
                        name=f"disease-{crop.lower()}-baseline",
                        task="disease_detection",
                        version="0.1.0",
                        backend="rules-and-crop-context",
                        status="baseline",
                        labels=["Healthy", f"{crop} Disease"],
                        explainability=["rules_fired", "evidence", "heatmap_hint"],
                        upgrade_path=f"Replace with trained {crop.lower()} disease classifier.",
                        crop=crop,
                    ))

        if "severity_estimation" not in trained_tasks:
            cards.append(VisionModelCard(
                name="severity-local-xai-baseline",
                task="severity_estimation",
                version="0.1.0",
                backend="risk-priors",
                status="baseline",
                labels=["none", "low", "moderate", "high"],
                explainability=["rules_fired", "evidence"],
                upgrade_path="Replace with lesion segmentation model and percentage leaf-area scoring.",
            ))

        return cards

    def has_trained_model(self, task: str, crop: str = "") -> bool:
        self._ensure_loaded()
        for card in self._trained_cards:
            if card.task == task:
                if not crop or card.crop.lower() == crop.lower():
                    return True
        return False
