"""Deprecated predictor names retained only for import compatibility.

Production inference is served exclusively by registered ONNX artifacts.
"""

from pathlib import Path

from app.models_ml.errors import ModelUnavailableError


class ExplainableCropPredictor:
    def predict(self, image: Path):
        raise ModelUnavailableError(
            "crop_classification",
            reason="Legacy metadata predictors are disabled. Register a trained crop model.",
        )


class ExplainableDiseasePredictor:
    def predict(self, crop: str, image: Path):
        raise ModelUnavailableError(
            "disease_classification",
            crop,
            "Legacy metadata predictors are disabled. Use a registered ONNX model.",
        )


class ExplainableSeverityPredictor:
    def predict(self, crop: str, disease: str, image: Path):
        raise ModelUnavailableError(
            "severity_estimation",
            crop,
            "Legacy metadata predictors are disabled. Use a registered ONNX model.",
        )
