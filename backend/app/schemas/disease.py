from datetime import datetime

from pydantic import BaseModel

from app.schemas.recommendation import RecommendationPayload


class PredictorOutput(BaseModel):
    label: str
    confidence: float
    evidence: list[str]
    rules_fired: list[str]
    heatmap_hint: str | None = None


class SeverityOutput(BaseModel):
    label: str
    score: float
    evidence: list[str]
    rules_fired: list[str]


class XAIDetectionOutput(BaseModel):
    bbox: list[int]
    class_label: str
    confidence: float
    area_pixels: int


class XAILesionRegionOutput(BaseModel):
    bbox: list[int]
    lesion_type: str
    area_ratio: float
    color_profile: dict
    texture_features: dict


class XAIUncertaintyOutput(BaseModel):
    aleatoric: float
    epistemic: float
    total: float
    calibration_score: float
    prediction_entropy: float
    warning: str | None = None


class XAIAgronomicOutput(BaseModel):
    disease_name: str
    causal_organism: str
    disease_stage: str
    spread_risk: str
    environmental_factors: list[str]
    treatment_urgency: str
    key_visual_indicators: list[str]
    differential_diagnosis: list[str]


class XAISeverityDetailOutput(BaseModel):
    lesion_area_ratio: float
    lesion_count: int
    largest_lesion_area: float
    affected_leaf_percentage: float
    color_degradation: float
    severity_score: float
    severity_label: str
    reasoning: list[str]


class XAIFeatureAttributionOutput(BaseModel):
    pixel_importance_available: bool
    top_contributing_regions: list[dict]
    gradient_norm: float


class XAIModelFeatureOutput(BaseModel):
    feature_name: str
    activation_strength: float
    spatial_location: str
    agronomic_mapping: str


class XAIReportOutput(BaseModel):
    detections: list[XAIDetectionOutput]
    lesion_regions: list[XAILesionRegionOutput]
    class_probabilities: dict[str, float]
    predicted_class: str
    confidence: float
    gradcam_available: bool
    attention_map_available: bool
    feature_attribution: XAIFeatureAttributionOutput
    severity: XAISeverityDetailOutput
    uncertainty: XAIUncertaintyOutput
    model_features: list[XAIModelFeatureOutput]
    agronomic: XAIAgronomicOutput
    pipeline_trace: list[dict]
    model_versions: dict[str, str]


class DiseaseAnalysisRead(BaseModel):
    prediction_id: int
    image_id: int | None
    crop: PredictorOutput
    disease: PredictorOutput
    severity: SeverityOutput
    weather: dict
    history: list[dict]
    recommendation: RecommendationPayload
    response: str
    trace: list[dict]
    created_at: datetime
    xai_report: XAIReportOutput | None = None
    xai_farmer_view: dict | None = None
