from app.config import get_settings
from app.weather.provider import LocalWeatherProvider, WeatherProvider


class WeatherService:
    def __init__(self, provider: WeatherProvider | None = None):
        if provider is not None:
            self.provider = provider
        else:
            self.provider = self._resolve_provider()

    def _resolve_provider(self) -> WeatherProvider:
        settings = get_settings()
        if settings.weather_provider == "openmeteo":
            try:
                from app.weather.openmeteo_provider import OpenMeteoWeatherProvider
                return OpenMeteoWeatherProvider()
            except Exception:
                pass
        return LocalWeatherProvider()

    def current(self, location: str | None = None) -> dict:
        return self.provider.current(location)

    def forecast(self, location: str | None = None, days: int = 5) -> dict:
        return self.provider.forecast(location, days)
