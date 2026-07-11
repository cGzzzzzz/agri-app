from pathlib import Path
from typing import Protocol

from app.vision.types import XAIPrediction, XAISeverity


class CropPredictor(Protocol):
    def predict(self, image: Path) -> XAIPrediction: ...


class DiseasePredictor(Protocol):
    def predict(self, crop: str, image: Path) -> XAIPrediction: ...


class SeverityPredictor(Protocol):
    def predict(self, crop: str, disease: str, image: Path) -> XAISeverity: ...
