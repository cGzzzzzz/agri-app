from unittest.mock import MagicMock

import pytest

from app.services.recommendation_engine import RecommendationEngine


@pytest.fixture
def engine():
    return RecommendationEngine()


class TestRecommendationEngine:
    def test_healthy_disease_returns_low_urgency(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Rice", status="available"),
            disease=MagicMock(label="Healthy", status="available"),
            severity=MagicMock(label="low", status="available"),
            weather={"precipitation_probability_percent": 20},
            history=[],
        )
        assert result["urgency"] == "low"
        assert "healthy" in result["title"].lower()

    def test_disease_present_returns_high_urgency(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Tomato", status="available"),
            disease=MagicMock(label="Bacterial Spot", status="available"),
            severity=MagicMock(label="moderate", status="available"),
            weather={"precipitation_probability_percent": 30},
            history=[],
        )
        assert result["urgency"] == "high"
        assert "Bacterial Spot" in result["title"]

    def test_high_severity_high_urgency(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Rice", status="available"),
            disease=MagicMock(label="Blast", status="available"),
            severity=MagicMock(label="high", status="available"),
            weather={},
            history=[],
        )
        assert result["urgency"] == "high"

    def test_rain_avoids_spraying(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Rice", status="available"),
            disease=MagicMock(label="Blast", status="available"),
            severity=MagicMock(label="low", status="available"),
            weather={"precipitation_probability_percent": 80},
            history=[],
        )
        assert any("Avoid" in c for c in result["weather_constraints"])

    def test_no_rain_allows_spraying(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Rice", status="available"),
            disease=MagicMock(label="Blast", status="available"),
            severity=MagicMock(label="low", status="available"),
            weather={"precipitation_probability_percent": 10},
            history=[],
        )
        assert any("can be scheduled" in c for c in result["weather_constraints"])

    def test_history_count_in_rationale(self, engine):
        history = [{"disease": "Blast", "severity": "high"}] * 5
        result = engine.generate(
            crop=MagicMock(label="Rice", status="available"),
            disease=MagicMock(label="Blast", status="available"),
            severity=MagicMock(label="low", status="available"),
            weather={},
            history=history,
        )
        assert "5 historical records" in result["rationale"]

    def test_dict_input_works(self, engine):
        result = engine.generate(
            crop={"label": "Rice", "status": "available"},
            disease={"label": "Healthy", "status": "available"},
            severity={"label": "low", "status": "available"},
            weather={},
            history=[],
        )
        assert result["urgency"] == "low"

    def test_output_has_all_required_keys(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Rice", status="available"),
            disease=MagicMock(label="Blast", status="available"),
            severity=MagicMock(label="moderate", status="available"),
            weather={"precipitation_probability_percent": 50},
            history=[],
        )
        for key in [
            "title",
            "action",
            "urgency",
            "rationale",
            "safety_notes",
            "weather_constraints",
            "next_steps",
            "xai",
        ]:
            assert key in result, f"Missing key: {key}"

    def test_healthy_safety_notes_no_chemical(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Rice", status="available"),
            disease=MagicMock(label="Healthy", status="available"),
            severity=MagicMock(label="low", status="available"),
            weather={},
            history=[],
        )
        assert any("No chemical" in n for n in result["safety_notes"])

    def test_unavailable_returns_review_required(self, engine):
        result = engine.generate(
            crop=MagicMock(label="Rice"),
            disease=MagicMock(label="unavailable"),
            severity=MagicMock(label="unavailable"),
            weather={},
            history=[],
        )
        assert result["urgency"] == "review_required"
        assert "unavailable" in result["title"].lower()
