from unittest.mock import MagicMock

from app.weather.service import WeatherService


class TestWeatherService:
    def test_local_provider_returns_data(self):
        mock_provider = MagicMock()
        mock_provider.current.return_value = {
            "temperature_c": 28,
            "humidity_percent": 75,
            "condition": "Partly Cloudy",
        }
        service = WeatherService(provider=mock_provider)
        result = service.current("Test Location")
        assert result["temperature_c"] == 28
        assert result["humidity_percent"] == 75

    def test_forecast_returns_list(self):
        mock_provider = MagicMock()
        mock_provider.forecast.return_value = [{"date": "2025-01-01", "high_c": 30, "low_c": 20}]
        service = WeatherService(provider=mock_provider)
        result = service.forecast("Test Location")
        assert len(result) >= 1

    def test_service_uses_injected_provider(self):
        mock_provider = MagicMock()
        service = WeatherService(provider=mock_provider)
        assert service.provider is mock_provider
