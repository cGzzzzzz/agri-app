from unittest.mock import patch

import pytest

from app.models_ml.disease.registry import DiseaseModelRegistry


class TestDiseaseModelRegistry:
    def test_supported_crops_has_all_trained_models(self):
        crops = DiseaseModelRegistry.supported_crops()
        for crop in ["rice", "tomato", "potato", "pepper"]:
            assert crop in crops

    def test_get_model_returns_instance(self):
        for crop in ["rice", "tomato", "potato", "pepper"]:
            model = DiseaseModelRegistry.get_model(crop)
            assert model is not None
            assert model.crop.lower() == crop

    def test_get_model_case_insensitive(self):
        model = DiseaseModelRegistry.get_model("Rice")
        assert model is not None
        assert model.crop == "Rice"

    def test_get_model_unknown_returns_none(self):
        assert DiseaseModelRegistry.get_model("mango") is None

    def test_get_classes(self):
        classes = DiseaseModelRegistry.get_classes("tomato")
        assert len(classes) == 10
        assert "Healthy" in classes

    def test_get_classes_unknown(self):
        assert DiseaseModelRegistry.get_classes("unknown") == []

    def test_register_crop_dynamic(self):
        class FakeModel:
            crop = "test_crop"
            class_names = ["disease_a"]
            model_name = "test_model"

            def _get_artifact_path(self):
                return None

            def _load_session(self):
                return False

        DiseaseModelRegistry.register_crop("test_crop", FakeModel)
        assert "test_crop" in DiseaseModelRegistry.supported_crops()
        model = DiseaseModelRegistry.get_model("test_crop")
        assert model.crop == "test_crop"
        del DiseaseModelRegistry._crop_models["test_crop"]


class TestBaseDiseaseModel:
    def test_predict_with_mocked_onnx(self, mock_onnx_session, sample_image):
        model = DiseaseModelRegistry.get_model("rice")
        with patch.object(model, "_try_load_session", return_value=mock_onnx_session):
            result = model.predict(sample_image)
        assert result is not None
        assert result.confidence > 0
        assert result.model_name == "Rice_disease_model"
        assert any("onnx_model" in r for r in result.rules_fired)

    def test_predict_raises_when_no_session(self, sample_image):
        from app.models_ml.errors import ModelUnavailableError

        model = DiseaseModelRegistry.get_model("rice")
        with (
            patch.object(model, "_try_load_session", return_value=None),
            pytest.raises(ModelUnavailableError),
        ):
            model.predict(sample_image)

    def test_all_models_have_valid_artifact_paths(self):
        for crop in ["rice", "tomato", "potato", "pepper"]:
            model = DiseaseModelRegistry.get_model(crop)
            path = model._get_artifact_path()
            assert path is not None
            assert path.name == "model.onnx"
