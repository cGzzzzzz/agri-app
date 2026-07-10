from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.vision.types import XAIPrediction, XAISeverity


@dataclass
class OrchestratorInput:
    user_id: int
    user_language: str
    image_path: str
    image_id: int | None
    farm_id: int | None
    crop_id: int | None
    crop_override: str | None = None
    include_xai_heatmap: bool = False


@dataclass
class OrchestratorContext:
    user: dict
    farm: dict | None
    crop: dict | None
    weather: dict
    history: list[dict]
    location: str | None = None


@dataclass
class ProcessedImage:
    image_path: Path
    pixels: object = None
    tensor: object = None
    original_size: tuple[int, int] = (0, 0)
    image_format: str = ""
    quality_warnings: list[str] = field(default_factory=list)


@dataclass
class CropPrediction:
    label: str
    confidence: float
    evidence: list[str]
    rules_fired: list[str]
    source: str
    model_name: str

    @classmethod
    def from_xai(cls, pred: XAIPrediction, source: str = "model") -> "CropPrediction":
        return cls(
            label=pred.label,
            confidence=pred.confidence,
            evidence=pred.evidence,
            rules_fired=pred.rules_fired,
            source=source,
            model_name=pred.model_name,
        )


@dataclass
class DiseasePrediction:
    label: str
    confidence: float
    evidence: list[str]
    rules_fired: list[str]
    heatmap_hint: str | None
    model_name: str

    @classmethod
    def from_xai(cls, pred: XAIPrediction) -> "DiseasePrediction":
        return cls(
            label=pred.label,
            confidence=pred.confidence,
            evidence=pred.evidence,
            rules_fired=pred.rules_fired,
            heatmap_hint=pred.heatmap_hint,
            model_name=pred.model_name,
        )


@dataclass
class SeverityEstimation:
    label: str
    score: float
    evidence: list[str]
    rules_fired: list[str]
    model_name: str

    @classmethod
    def from_xai(cls, sev: XAISeverity) -> "SeverityEstimation":
        return cls(
            label=sev.label,
            score=sev.score,
            evidence=sev.evidence,
            rules_fired=sev.rules_fired,
            model_name=sev.model_name,
        )


@dataclass
class OrchestratorResult:
    prediction_id: int | None
    image_id: int | None
    crop: CropPrediction
    disease: DiseasePrediction
    severity: SeverityEstimation
    weather: dict
    history: list[dict]
    recommendation: dict
    response: str
    trace: list[dict]
    created_at: datetime
