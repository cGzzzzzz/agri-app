"""Vision subsystem for crop and disease analysis."""

from app.vision.baselines import ExplainableCropPredictor, ExplainableDiseasePredictor, ExplainableSeverityPredictor
from app.vision.gradcam import GradCAMGenerator
from app.vision.image_processor import RealImagePreprocessor
from app.vision.interfaces import CropPredictor, DiseasePredictor, SeverityPredictor
from app.vision.model_registry import VisionModelRegistry
from app.vision.pipeline import VisionPipeline
from app.vision.preprocessing import ImagePreprocessor
from app.vision.types import VisionAnalysis, VisionFeatures, VisionInput, VisionModelCard, XAIPrediction, XAISeverity

__all__ = [
    "CropPredictor",
    "DiseasePredictor",
    "ExplainableCropPredictor",
    "ExplainableDiseasePredictor",
    "ExplainableSeverityPredictor",
    "GradCAMGenerator",
    "ImagePreprocessor",
    "RealImagePreprocessor",
    "SeverityPredictor",
    "VisionAnalysis",
    "VisionFeatures",
    "VisionInput",
    "VisionModelCard",
    "VisionModelRegistry",
    "VisionPipeline",
    "XAIPrediction",
    "XAISeverity",
]
