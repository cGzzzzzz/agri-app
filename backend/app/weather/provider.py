from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone


class WeatherProvider(ABC):
    @abstractmethod
    def current(self, location: str | None = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def forecast(self, location: str | None = None, days: int = 5) -> dict:
        raise NotImplementedError


class LocalWeatherProvider(WeatherProvider):
    def current(self, location: str | None = None) -> dict:
        return {
            "location": location or "Local Farm",
            "temperature_c": 31.0,
            "condition": "Humid with possible rain",
            "humidity_percent": 84,
            "precipitation_probability_percent": 68,
            "wind_kph": 9.0,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "advisory": "Disease pressure is elevated; avoid spraying during rain windows.",
        }

    def forecast(self, location: str | None = None, days: int = 5) -> dict:
        start = datetime.now(timezone.utc).date()
        forecast_days = []
        for index in range(days):
            rain = max(20, 70 - index * 8)
            forecast_days.append(
                {
                    "date": str(start + timedelta(days=index)),
                    "condition": "Rain likely" if rain >= 50 else "Partly cloudy",
                    "min_temp_c": 24.0,
                    "max_temp_c": 32.0,
                    "rain_probability_percent": rain,
                    "advisory": "Delay foliar spray" if rain >= 50 else "Suitable spray window possible",
                }
            )
        return {"location": location or "Local Farm", "days": forecast_days}
