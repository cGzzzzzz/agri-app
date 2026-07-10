from pathlib import Path

from app.orchestrator.input_types import CropPrediction
from app.vision.baselines import ExplainableCropPredictor


class CropResolver:
    def __init__(self):
        self.baseline = ExplainableCropPredictor()

    def resolve(self, state: dict) -> CropPrediction:
        input_data = state.get("input")
        context = state.get("context")
        processed = state.get("image_preprocessing")

        image_path = Path(input_data.image_path)

        if input_data.crop_override:
            return CropPrediction(
                label=input_data.crop_override,
                confidence=1.0,
                evidence=[
                    f"User-specified crop override: {input_data.crop_override}",
                    "Context override takes highest priority.",
                ],
                rules_fired=["context_override:user_specified"],
                source="context_override",
                model_name="user_override",
            )

        if context and context.crop:
            crop_type = context.crop.get("crop_type", "")
            if crop_type:
                return CropPrediction(
                    label=crop_type,
                    confidence=0.95,
                    evidence=[
                        f"Registered crop from farm profile: {crop_type}",
                        "Registered crop context overrides baseline crop classifier.",
                    ],
                    rules_fired=["context_override:registered_crop"],
                    source="context_override",
                    model_name="farm_profile",
                )

        try:
            from app.models_ml.registry.model_registry import ModelRegistry
            from app.config import get_settings

            settings = get_settings()
            registry = ModelRegistry(settings.model_artifacts_dir)
            registry.discover()
            loaded = registry.load_latest("crop_classification")
            if loaded:
                from app.models_ml.crop.classifier import ONNXCropClassifier

                classifier = ONNXCropClassifier(
                    session=loaded.session,
                    class_names=loaded.metadata.classes,
                )
                pred = classifier.predict(image_path)
                return CropPrediction.from_xai(pred, source="model")
        except Exception:
            pass

        xai_pred = self.baseline.predict(image_path)
        return CropPrediction.from_xai(xai_pred, source="baseline")
