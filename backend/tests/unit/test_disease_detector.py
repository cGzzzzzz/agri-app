from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.orchestrator.disease_detector import (
    DiseaseDetector,
    SeverityEstimatorStage,
)


@pytest.fixture
def detector():
    return DiseaseDetector()


@pytest.fixture
def severity_stage():
    return SeverityEstimatorStage()


class TestDiseaseDetector:
    def _make_state(self, crop_label="Rice", image_path=None):
        return {
            "crop_resolution": MagicMock(
                label=crop_label,
                confidence=0.9,
                evidence=[],
                rules_fired=[],
                source="model",
                status="available",
            ),
            "image_preprocessing": MagicMock(),
            "input": MagicMock(image_path=str(image_path or Path("/tmp/fake.jpg"))),
            "_hybrid_result": None,
        }

    def test_onnx_used_when_hybrid_none(self, detector, sample_image):
        state = self._make_state("Rice", sample_image)
        with patch("app.models_ml.disease.registry.DiseaseModelRegistry.predict") as mock_predict:
            mock_pred = MagicMock()
            mock_pred.label = "Bacterial Leaf Blight"
            mock_pred.confidence = 0.95
            mock_pred.evidence = []
            mock_pred.rules_fired = ["onnx_model:Rice"]
            mock_pred.model_name = "Rice"
            mock_predict.return_value = mock_pred
            result = detector.detect(state)
        assert result.label == "Bacterial Leaf Blight"

    def test_unavailable_when_no_model(self, detector, sample_image):
        state = self._make_state("Rice", sample_image)
        with patch(
            "app.models_ml.disease.registry.DiseaseModelRegistry.predict", return_value=None
        ):
            result = detector.detect(state)
        assert result.status == "unavailable"
        assert result.label == "model_unavailable"

    def test_unavailable_when_crop_unavailable(self, detector, sample_image):
        state = self._make_state("Rice", sample_image)
        state["crop_resolution"] = MagicMock(
            status="unavailable", unavailable_reason="no crop classifier"
        )
        result = detector.detect(state)
        assert result.status == "unavailable"


class TestSeverityEstimator:
    def _make_state(self, crop="Rice", disease="Blast", image_path=None):
        return {
            "crop_resolution": MagicMock(label=crop),
            "disease_detection": MagicMock(
                label=disease,
                confidence=0.9,
                evidence=[],
                rules_fired=[],
                model_name="test",
                status="available",
            ),
            "image_preprocessing": MagicMock(),
            "input": MagicMock(image_path=str(image_path or Path("/tmp/fake.jpg"))),
            "_hybrid_result": None,
        }

    def test_onnx_severity_first(self, severity_stage, sample_image):
        state = self._make_state(image_path=sample_image)
        mock_result = MagicMock()
        mock_result.label = "moderate"
        mock_result.score = 0.75
        mock_result.evidence = []
        mock_result.rules_fired = ["onnx_model:severity"]
        mock_result.model_name = "onnx"
        with patch("app.models_ml.severity.estimator.ONNXSeverityEstimator") as MockEst:
            mock_est = MagicMock()
            mock_est.predict.return_value = mock_result
            MockEst.return_value = mock_est
            result = severity_stage.estimate(state)
        assert result.label == "moderate"

    def test_unavailable_when_disease_unavailable(self, severity_stage, sample_image):
        state = self._make_state(image_path=sample_image)
        state["disease_detection"] = MagicMock(
            status="unavailable", unavailable_reason="no disease model"
        )
        result = severity_stage.estimate(state)
        assert result.status == "unavailable"
        assert result.label == "model_unavailable"

    def test_unavailable_when_onnx_fails(self, severity_stage, sample_image):
        state = self._make_state(image_path=sample_image)
        with patch(
            "app.models_ml.severity.estimator.ONNXSeverityEstimator",
            side_effect=Exception("ONNX fail"),
        ):
            result = severity_stage.estimate(state)
        assert result.status == "unavailable"
        assert result.label == "model_unavailable"
