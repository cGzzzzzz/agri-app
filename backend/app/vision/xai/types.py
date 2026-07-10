from dataclasses import dataclass, field


@dataclass
class ColorProfile:
    dominant_hue: float = 0.0
    saturation_mean: float = 0.0
    brightness_mean: float = 0.0
    green_ratio: float = 0.0
    brown_ratio: float = 0.0
    gray_ratio: float = 0.0

    def to_dict(self) -> dict:
        return {
            "dominant_hue": round(self.dominant_hue, 2),
            "saturation_mean": round(self.saturation_mean, 2),
            "brightness_mean": round(self.brightness_mean, 2),
            "green_ratio": round(self.green_ratio, 3),
            "brown_ratio": round(self.brown_ratio, 3),
            "gray_ratio": round(self.gray_ratio, 3),
        }


@dataclass
class TextureFeatures:
    edge_density: float = 0.0
    contrast: float = 0.0
    homogeneity: float = 0.0
    is_necrotic: bool = False

    def to_dict(self) -> dict:
        return {
            "edge_density": round(self.edge_density, 4),
            "contrast": round(self.contrast, 4),
            "homogeneity": round(self.homogeneity, 4),
            "is_necrotic": self.is_necrotic,
        }


@dataclass
class LesionRegion:
    crop_image_base64: str = ""
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    lesion_type: str = ""
    area_ratio: float = 0.0
    color_profile: ColorProfile = field(default_factory=ColorProfile)
    texture_features: TextureFeatures = field(default_factory=TextureFeatures)

    def to_dict(self) -> dict:
        return {
            "bbox": list(self.bbox),
            "lesion_type": self.lesion_type,
            "area_ratio": round(self.area_ratio, 4),
            "color_profile": self.color_profile.to_dict(),
            "texture_features": self.texture_features.to_dict(),
        }


@dataclass
class RegionContribution:
    region_description: str = ""
    contribution_score: float = 0.0
    feature_type: str = ""

    def to_dict(self) -> dict:
        return {
            "region_description": self.region_description,
            "contribution_score": round(self.contribution_score, 4),
            "feature_type": self.feature_type,
        }


@dataclass
class FeatureAttribution:
    pixel_importance_map: str = ""
    top_contributing_regions: list[RegionContribution] = field(default_factory=list)
    gradient_norm: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pixel_importance_available": bool(self.pixel_importance_map),
            "top_contributing_regions": [r.to_dict() for r in self.top_contributing_regions],
            "gradient_norm": round(self.gradient_norm, 4),
        }


@dataclass
class ModelFeature:
    feature_name: str = ""
    activation_strength: float = 0.0
    spatial_location: str = ""
    agronomic_mapping: str = ""

    def to_dict(self) -> dict:
        return {
            "feature_name": self.feature_name,
            "activation_strength": round(self.activation_strength, 4),
            "spatial_location": self.spatial_location,
            "agronomic_mapping": self.agronomic_mapping,
        }


@dataclass
class UncertaintyEstimate:
    aleatoric: float = 0.0
    epistemic: float = 0.0
    total: float = 0.0
    calibration_score: float = 0.0
    prediction_entropy: float = 0.0
    warning: str | None = None

    def to_dict(self) -> dict:
        return {
            "aleatoric": round(self.aleatoric, 4),
            "epistemic": round(self.epistemic, 4),
            "total": round(self.total, 4),
            "calibration_score": round(self.calibration_score, 4),
            "prediction_entropy": round(self.prediction_entropy, 4),
            "warning": self.warning,
        }


@dataclass
class SeverityExplanation:
    lesion_area_ratio: float = 0.0
    lesion_count: int = 0
    largest_lesion_area: float = 0.0
    affected_leaf_percentage: float = 0.0
    color_degradation: float = 0.0
    severity_score: float = 0.0
    severity_label: str = "none"
    reasoning: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lesion_area_ratio": round(self.lesion_area_ratio, 4),
            "lesion_count": self.lesion_count,
            "largest_lesion_area": round(self.largest_lesion_area, 4),
            "affected_leaf_percentage": round(self.affected_leaf_percentage * 100, 1),
            "color_degradation": round(self.color_degradation, 4),
            "severity_score": round(self.severity_score, 4),
            "severity_label": self.severity_label,
            "reasoning": self.reasoning,
        }


@dataclass
class AgronomicInterpretation:
    disease_name: str = ""
    causal_organism: str = ""
    disease_stage: str = ""
    spread_risk: str = ""
    environmental_factors: list[str] = field(default_factory=list)
    treatment_urgency: str = ""
    key_visual_indicators: list[str] = field(default_factory=list)
    differential_diagnosis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "disease_name": self.disease_name,
            "causal_organism": self.causal_organism,
            "disease_stage": self.disease_stage,
            "spread_risk": self.spread_risk,
            "environmental_factors": self.environmental_factors,
            "treatment_urgency": self.treatment_urgency,
            "key_visual_indicators": self.key_visual_indicators,
            "differential_diagnosis": self.differential_diagnosis,
        }


@dataclass
class Detection:
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    class_label: str = ""
    confidence: float = 0.0
    area_pixels: int = 0

    def to_dict(self) -> dict:
        return {
            "bbox": list(self.bbox),
            "class_label": self.class_label,
            "confidence": round(self.confidence, 4),
            "area_pixels": self.area_pixels,
        }


@dataclass
class XAIReport:
    detections: list[Detection] = field(default_factory=list)
    lesion_regions: list[LesionRegion] = field(default_factory=list)
    class_probabilities: dict[str, float] = field(default_factory=dict)
    predicted_class: str = ""
    confidence: float = 0.0
    gradcam_heatmap: str = ""
    attention_map: str = ""
    feature_attribution: FeatureAttribution = field(default_factory=FeatureAttribution)
    severity: SeverityExplanation = field(default_factory=SeverityExplanation)
    uncertainty: UncertaintyEstimate = field(default_factory=UncertaintyEstimate)
    model_features: list[ModelFeature] = field(default_factory=list)
    agronomic: AgronomicInterpretation = field(default_factory=AgronomicInterpretation)
    pipeline_trace: list[dict] = field(default_factory=list)
    model_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "lesion_regions": [r.to_dict() for r in self.lesion_regions],
            "class_probabilities": self.class_probabilities,
            "predicted_class": self.predicted_class,
            "confidence": round(self.confidence, 4),
            "gradcam_available": bool(self.gradcam_heatmap),
            "attention_map_available": bool(self.attention_map),
            "feature_attribution": self.feature_attribution.to_dict(),
            "severity": self.severity.to_dict(),
            "uncertainty": self.uncertainty.to_dict(),
            "model_features": [f.to_dict() for f in self.model_features],
            "agronomic": self.agronomic.to_dict(),
            "pipeline_trace": self.pipeline_trace,
            "model_versions": self.model_versions,
        }

    def to_farmer_view(self) -> dict:
        return {
            "disease": self.predicted_class,
            "confidence": f"{self.confidence:.0%}",
            "severity": self.severity.severity_label.upper(),
            "severity_score": f"{self.severity.severity_score:.0%}",
            "detection": {
                "regions_found": len(self.detections),
                "lesion_count": self.severity.lesion_count,
                "leaf_area_affected": f"{self.severity.affected_leaf_percentage:.0%}",
            },
            "explanation": {
                "what_model_saw": self.agronomic.key_visual_indicators[:3] if self.agronomic.key_visual_indicators else [],
                "confidence_detail": self.class_probabilities,
                "reliability": self.uncertainty.warning or "High — well-calibrated prediction",
            },
            "agronomic": {
                "disease_stage": self.agronomic.disease_stage,
                "spread_risk": self.agronomic.spread_risk,
                "treatment_urgency": self.agronomic.treatment_urgency,
            },
        }
