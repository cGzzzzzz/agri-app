from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VisionInput:
    image_path: Path
    crop_hint: str | None = None


@dataclass
class VisionFeatures:
    filename: str
    extension: str
    size_bytes: int
    image_signature: str
    quality_warnings: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)


@dataclass
class VisionModelCard:
    name: str
    task: str
    version: str
    backend: str
    status: str
    labels: list[str]
    explainability: list[str]
    upgrade_path: str
    framework: str = "rules"
    crop: str = ""
    classes: list[str] = field(default_factory=list)
    input_shape: list[int] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class XAIPrediction:
    label: str
    confidence: float
    evidence: list[str]
    rules_fired: list[str]
    heatmap_hint: str | None = None
    model_name: str = ""
    status: str = "available"
    unavailable_reason: str | None = None


@dataclass
class XAISeverity:
    label: str
    score: float
    evidence: list[str]
    rules_fired: list[str]
    model_name: str = ""
    status: str = "available"
    unavailable_reason: str | None = None


@dataclass
class VisionAnalysis:
    features: VisionFeatures
    crop: XAIPrediction
    disease: XAIPrediction
    severity: XAISeverity
    trace: list[dict]
    model_cards: list[VisionModelCard]
    gradcam_heatmap: str | None = None
