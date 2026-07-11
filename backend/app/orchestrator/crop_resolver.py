from pathlib import Path

from app.models_ml.errors import ModelUnavailableError
from app.orchestrator.input_types import CropPrediction


class CropResolver:
    def resolve(self, state: dict) -> CropPrediction:
        input_data = state.get("input")
        context = state.get("context")
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
                        "Registered crop context is the authoritative crop selection.",
                    ],
                    rules_fired=["context_override:registered_crop"],
                    source="context_override",
                    model_name="farm_profile",
                )

        try:
            from app.config import get_settings
            from app.models_ml.registry.model_registry import ModelRegistry

            settings = get_settings()
            registry = ModelRegistry(settings.model_artifacts_dir)
            registry.discover()
            loaded = registry.load_latest("crop_classification")
            if loaded is None:
                raise ModelUnavailableError("crop_classification")
            from app.models_ml.crop.classifier import ONNXCropClassifier

            classifier = ONNXCropClassifier(
                session=loaded.session, class_names=loaded.metadata.classes
            )
            return CropPrediction.from_xai(classifier.predict(image_path), source="model")
        except Exception as exc:
            return CropPrediction(
                label="unknown",
                confidence=0.0,
                evidence=[
                    "No crop context was supplied and no trained crop classifier is registered."
                ],
                rules_fired=["model_registry:crop_classifier_unavailable"],
                source="model_unavailable",
                model_name="",
                status="unavailable",
                unavailable_reason=str(exc),
            )
