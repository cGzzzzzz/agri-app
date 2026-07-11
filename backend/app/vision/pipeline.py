from dataclasses import asdict
from pathlib import Path

from app.vision.gradcam import GradCAMGenerator
from app.vision.image_processor import RealImagePreprocessor
from app.vision.interfaces import CropPredictor, DiseasePredictor, SeverityPredictor
from app.vision.model_registry import VisionModelRegistry
from app.vision.preprocessing import ImagePreprocessor
from app.vision.types import VisionAnalysis, VisionInput


class VisionPipeline:
    def __init__(
        self,
        crop_predictor: CropPredictor,
        disease_predictor: DiseasePredictor,
        severity_predictor: SeverityPredictor,
        preprocessor: ImagePreprocessor | None = None,
        real_preprocessor: RealImagePreprocessor | None = None,
        registry: VisionModelRegistry | None = None,
        gradcam: GradCAMGenerator | None = None,
    ):
        self.crop_predictor = crop_predictor
        self.disease_predictor = disease_predictor
        self.severity_predictor = severity_predictor
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.real_preprocessor = real_preprocessor or RealImagePreprocessor()
        self.registry = registry or VisionModelRegistry()
        self.gradcam = gradcam or GradCAMGenerator()

    def analyze(
        self,
        image: Path,
        crop_override: str | None = None,
        include_heatmap: bool = False,
    ) -> VisionAnalysis:
        trace: list[dict] = []

        features = self.preprocessor.inspect(VisionInput(image, crop_override))
        trace.append(
            {"step": "image_preprocessing", "status": "completed", "data": asdict(features)}
        )

        try:
            processed = self.real_preprocessor.process(image, crop_override)
            trace.append(
                {
                    "step": "real_image_processing",
                    "status": "completed",
                    "data": {
                        "original_size": list(processed.original_size),
                        "format": processed.image_format,
                        "quality_warnings": processed.quality_warnings,
                        "tensor_shape": list(processed.tensor.shape),
                    },
                }
            )
        except Exception as e:
            processed = None
            trace.append({"step": "real_image_processing", "status": "failed", "error": str(e)})

        crop = self.crop_predictor.predict(image)
        if crop_override:
            crop.label = crop_override
            crop.evidence.append("Registered crop context overrides baseline crop classifier.")
            crop.rules_fired.append("context_override:registered_crop")
        trace.append({"step": "crop_detection", "status": "completed", "data": asdict(crop)})

        disease = self.disease_predictor.predict(crop.label, image)
        trace.append({"step": "disease_detection", "status": "completed", "data": asdict(disease)})

        severity = self.severity_predictor.predict(crop.label, disease.label, image)
        trace.append(
            {"step": "severity_estimation", "status": "completed", "data": asdict(severity)}
        )

        model_cards = self.registry.active_cards()
        trace.append(
            {
                "step": "model_registry",
                "status": "completed",
                "data": [asdict(card) for card in model_cards],
            }
        )

        gradcam_b64 = None
        if include_heatmap and processed is not None:
            try:
                from app.config import get_settings
                from app.models_ml.registry.model_registry import ModelRegistry as ProdRegistry

                settings = get_settings()
                prod_registry = ProdRegistry(settings.model_artifacts_dir)
                prod_registry.discover()
                loaded = prod_registry.load_latest("disease_detection", crop.label)
                if loaded:
                    gradcam_b64 = self.gradcam.generate_heatmap(
                        loaded.session,
                        processed.tensor,
                        input_name=loaded.session.get_inputs()[0].name,
                    )
            except Exception:
                pass
            trace.append(
                {
                    "step": "gradcam",
                    "status": "completed" if gradcam_b64 else "skipped",
                    "data": {"available": gradcam_b64 is not None},
                }
            )

        return VisionAnalysis(
            features=features,
            crop=crop,
            disease=disease,
            severity=severity,
            trace=trace,
            model_cards=model_cards,
            gradcam_heatmap=gradcam_b64,
        )
