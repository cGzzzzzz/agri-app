from pathlib import Path

from app.vision.preprocessing import ImagePreprocessor
from app.vision.types import XAIPrediction, XAISeverity, VisionInput


class ExplainableCropPredictor:
    model_name = "crop-local-xai-baseline"

    def __init__(self):
        self.preprocessor = ImagePreprocessor()

    def predict(self, image: Path) -> XAIPrediction:
        features = self.preprocessor.inspect(VisionInput(image))
        tokens = set(features.tokens)
        if {"rice", "paddy"} & tokens:
            crop, confidence, rules = "Rice", 0.84, ["token_hint:rice_or_paddy"]
        elif "tomato" in tokens:
            crop, confidence, rules = "Tomato", 0.81, ["token_hint:tomato"]
        elif "wheat" in tokens:
            crop, confidence, rules = "Wheat", 0.79, ["token_hint:wheat"]
        else:
            crop, confidence, rules = "Rice", 0.62, ["fallback:regional_priority_crop", "fallback:leaf_texture_prior"]

        evidence = [
            f"Image signature: {features.image_signature}",
            f"File size: {features.size_bytes} bytes",
            "Baseline crop classifier uses local metadata and crop priors until trained weights are installed.",
        ]
        evidence.extend(features.quality_warnings)
        return XAIPrediction(
            label=crop,
            confidence=confidence,
            evidence=evidence,
            rules_fired=rules,
            heatmap_hint="Inspect the full leaf outline and dominant vegetation region.",
            model_name=self.model_name,
        )


class ExplainableDiseasePredictor:
    model_name = "disease-local-xai-baseline"

    def __init__(self):
        self.preprocessor = ImagePreprocessor()

    def predict(self, crop: str, image: Path) -> XAIPrediction:
        features = self.preprocessor.inspect(VisionInput(image, crop))
        tokens = set(features.tokens)
        crop_key = crop.lower()

        if "healthy" in tokens:
            label, confidence, rules = "Healthy", 0.75, ["token_hint:healthy"]
        elif crop_key == "rice" and ({"blast", "spot", "lesion"} & tokens):
            label, confidence, rules = "Rice Blast", 0.9, ["crop:rice", "symptom_prior:spindle_or_spot_lesions"]
        elif crop_key == "tomato":
            label, confidence, rules = "Early Blight", 0.82, ["crop:tomato", "symptom_prior:concentric_spots"]
        elif crop_key == "wheat":
            label, confidence, rules = "Leaf Rust", 0.8, ["crop:wheat", "symptom_prior:rust_pustules"]
        else:
            label, confidence, rules = "Rice Blast", 0.69, ["fallback:most_likely_leaf_disease", f"crop:{crop_key}"]

        evidence = [
            f"Crop context: {crop}",
            f"Image signature: {features.image_signature}",
            "Disease baseline ranks likely plant diseases using crop context and symptom tokens.",
        ]
        evidence.extend(features.quality_warnings)
        return XAIPrediction(
            label=label,
            confidence=confidence,
            evidence=evidence,
            rules_fired=rules,
            heatmap_hint="Focus on spot margins, chlorotic halos, lesion clustering, and necrotic leaf areas.",
            model_name=self.model_name,
        )


class ExplainableSeverityPredictor:
    model_name = "severity-local-xai-baseline"

    def __init__(self):
        self.preprocessor = ImagePreprocessor()

    def predict(self, crop: str, disease: str, image: Path) -> XAISeverity:
        features = self.preprocessor.inspect(VisionInput(image, crop))
        tokens = set(features.tokens)
        if disease.lower() == "healthy":
            label, score, rules = "none", 0.05, ["disease:healthy"]
        elif "severe" in tokens or features.size_bytes > 4_000_000:
            label, score, rules = "high", 0.78, ["risk_hint:large_or_severe_image"]
        elif features.size_bytes < 128:
            label, score, rules = "low", 0.28, ["quality_warning:very_small_image"]
        else:
            label, score, rules = "moderate", 0.52, ["lesion_coverage_prior:moderate", f"disease:{disease.lower()}"]

        evidence = [
            f"Crop context: {crop}",
            f"Disease context: {disease}",
            "Severity baseline estimates risk until lesion segmentation is installed.",
        ]
        evidence.extend(features.quality_warnings)
        return XAISeverity(label=label, score=score, evidence=evidence, rules_fired=rules, model_name=self.model_name)
