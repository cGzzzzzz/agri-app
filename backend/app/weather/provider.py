from abc import ABC, abstractmethod
from datetime import UTC, datetime


class WeatherProvider(ABC):
    @abstractmethod
    def current(self, location: str | None = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def forecast(self, location: str | None = None, days: int = 5) -> dict:
        raise NotImplementedError


class UnavailableWeatherProvider(WeatherProvider):
    def __init__(self, reason: str = "No local weather provider has been configured."):
        self.reason = reason

    def current(self, location: str | None = None) -> dict:
        return {
            "location": location,
            "temperature_c": None,
            "condition": "unavailable",
            "humidity_percent": None,
            "precipitation_probability_percent": None,
            "wind_kph": None,
            "observed_at": datetime.now(UTC).isoformat(),
            "advisory": "Weather-dependent advice is unavailable until a provider is configured.",
            "source": "unavailable",
            "status": "unavailable",
            "reason": self.reason,
        }

    def forecast(self, location: str | None = None, days: int = 5) -> dict:
        return {
            "location": location,
            "days": [],
            "source": "unavailable",
            "status": "unavailable",
            "reason": self.reason,
        }
