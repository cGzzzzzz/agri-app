from unittest.mock import MagicMock

import pytest

from app.orchestrator.crop_resolver import CropResolver


@pytest.fixture
def resolver():
    return CropResolver()


class TestCropResolverPriority:
    def test_user_override_highest_priority(self, resolver, sample_image):
        state = {
            "input": MagicMock(crop_override="Tomato", image_path=str(sample_image)),
            "context": MagicMock(crop=MagicMock(get=MagicMock(return_value="Rice"))),
        }
        state["context"].crop = {"crop_type": "Rice"}
        result = resolver.resolve(state)
        assert result.label == "Tomato"
        assert result.source == "context_override"

    def test_registered_crop_second_priority(self, resolver, sample_image):
        state = {
            "input": MagicMock(crop_override=None, image_path=str(sample_image)),
            "context": MagicMock(),
        }
        state["context"].crop = {"crop_type": "Rice"}
        result = resolver.resolve(state)
        assert result.label == "Rice"
        assert result.source == "context_override"
        assert "registered_crop" in result.rules_fired[0]

    def test_no_context_falls_to_model_unavailable(self, resolver, sample_image):
        state = {
            "input": MagicMock(crop_override=None, image_path=str(sample_image)),
            "context": MagicMock(crop=None),
        }
        state["context"].crop = None
        result = resolver.resolve(state)
        assert result is not None
        assert result.status == "unavailable"
