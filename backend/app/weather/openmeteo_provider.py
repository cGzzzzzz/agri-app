import logging
from datetime import UTC, datetime

import httpx

from app.weather.provider import WeatherProvider

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoWeatherProvider(WeatherProvider):
    def __init__(self):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._cache_ttl = 1800.0

    def _get_cached(self, key: str) -> dict | None:
        if key in self._cache:
            ts, data = self._cache[key]
            if (datetime.now(UTC).timestamp() - ts) < self._cache_ttl:
                return data
        return None

    def _set_cached(self, key: str, data: dict) -> None:
        self._cache[key] = (datetime.now(UTC).timestamp(), data)

    def _geocode(self, location: str) -> tuple[float, float] | None:
        cache_key = f"geo:{location}"
        cached = self._get_cached(cache_key)
        if cached:
            return (cached["lat"], cached["lon"])

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    GEOCODE_URL, params={"name": location, "count": 1, "language": "en"}
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                if results:
                    lat = results[0]["latitude"]
                    lon = results[0]["longitude"]
                    self._set_cached(cache_key, {"lat": lat, "lon": lon})
                    return (lat, lon)
        except Exception:
            logger.warning("Geocoding failed for: %s", location, exc_info=True)
        return None

    def current(self, location: str | None = None) -> dict:
        cache_key = f"current:{location}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        coords = self._geocode(location or "Tamil Nadu, India")
        if coords is None:
            return self._unavailable_current(
                location, "Location could not be resolved by the configured weather provider."
            )

        lat, lon = coords
        return self._fetch_current(lat, lon, location)

    def current_by_coords(self, lat: float, lng: float) -> dict:
        cache_key = f"current_coords:{lat:.4f}:{lng:.4f}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = self._fetch_current(lat, lng, f"{lat},{lng}")
        if result.get("status") != "unavailable":
            self._set_cached(cache_key, result)
        return result

    def _fetch_current(self, lat: float, lon: float, location_label: str | None) -> dict:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    WEATHER_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
                        "timezone": "auto",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                current = data.get("current", {})

                temp = current.get("temperature_2m")
                humidity = current.get("relative_humidity_2m")
                rain_prob = current.get("precipitation_probability")
                wind = current.get("wind_speed_10m")
                weather_code = current.get("weather_code", 0)
                if temp is None or humidity is None or rain_prob is None or wind is None:
                    return self._unavailable_current(
                        location_label,
                        "Weather provider returned an incomplete current observation.",
                    )

                condition = self._decode_weather_code(weather_code)
                advisory = self._generate_advisory(temp, humidity, rain_prob, condition)

                return {
                    "location": location_label or "Unknown",
                    "temperature_c": temp,
                    "condition": condition,
                    "humidity_percent": humidity,
                    "precipitation_probability_percent": rain_prob,
                    "wind_kph": wind,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "advisory": advisory,
                    "source": "open-meteo",
                }
        except Exception:
            logger.warning("Open-Meteo API failed", exc_info=True)
            return self._unavailable_current(
                location_label, "Configured weather provider request failed."
            )

    def forecast(self, location: str | None = None, days: int = 5) -> dict:
        cache_key = f"forecast:{location}:{days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        coords = self._geocode(location or "Tamil Nadu, India")
        if coords is None:
            return self._unavailable_forecast(
                location, "Location could not be resolved by the configured weather provider."
            )

        lat, lon = coords
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    WEATHER_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                        "timezone": "auto",
                        "forecast_days": days,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                daily = data.get("daily", {})

                forecast_days = []
                dates = daily.get("time", [])
                for i, date in enumerate(dates):
                    rain = (
                        daily.get("precipitation_probability_max", [0] * days)[i]
                        if i < len(daily.get("precipitation_probability_max", []))
                        else 0
                    )
                    tmax = (
                        daily.get("temperature_2m_max", [32] * days)[i]
                        if i < len(daily.get("temperature_2m_max", []))
                        else 32
                    )
                    tmin = (
                        daily.get("temperature_2m_min", [24] * days)[i]
                        if i < len(daily.get("temperature_2m_min", []))
                        else 24
                    )
                    wcode = (
                        daily.get("weather_code", [0] * days)[i]
                        if i < len(daily.get("weather_code", []))
                        else 0
                    )

                    condition = self._decode_weather_code(wcode)
                    forecast_days.append(
                        {
                            "date": date,
                            "condition": condition,
                            "min_temp_c": tmin,
                            "max_temp_c": tmax,
                            "rain_probability_percent": rain,
                            "advisory": "Delay foliar spray"
                            if rain >= 50
                            else "Suitable spray window possible",
                        }
                    )

                result = {
                    "location": location or "Unknown",
                    "days": forecast_days,
                    "source": "open-meteo",
                }
                self._set_cached(cache_key, result)
                return result
        except Exception:
            logger.warning("Open-Meteo forecast failed", exc_info=True)
            return self._unavailable_forecast(
                location, "Configured weather provider request failed."
            )

    def _decode_weather_code(self, code: int) -> str:
        codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail",
        }
        return codes.get(code, f"Weather code {code}")

    def _generate_advisory(
        self, temp: float, humidity: float, rain_prob: float, condition: str
    ) -> str:
        advisories = []
        if rain_prob >= 60:
            advisories.append("High rain probability - avoid foliar sprays.")
        elif rain_prob >= 40:
            advisories.append("Moderate rain chance - spray early morning if needed.")

        if humidity >= 85:
            advisories.append("High humidity increases fungal disease pressure.")
        elif humidity >= 70:
            advisories.append("Moderate humidity - monitor for disease symptoms.")

        if temp >= 35:
            advisories.append("High temperature stress possible. Ensure adequate irrigation.")
        elif temp <= 15:
            advisories.append("Cool temperatures may slow crop growth.")

        if not advisories:
            advisories.append("Favorable conditions for crop management.")

        return " ".join(advisories)

    def _unavailable_current(self, location: str | None, reason: str) -> dict:
        return {
            "location": location,
            "temperature_c": None,
            "condition": "unavailable",
            "humidity_percent": None,
            "precipitation_probability_percent": None,
            "wind_kph": None,
            "observed_at": datetime.now(UTC).isoformat(),
            "advisory": "Weather-dependent advice is unavailable until the provider returns an observation.",
            "source": "open-meteo",
            "status": "unavailable",
            "reason": reason,
        }

    def _unavailable_forecast(self, location: str | None, reason: str) -> dict:
        return {
            "location": location,
            "days": [],
            "source": "open-meteo",
            "status": "unavailable",
            "reason": reason,
        }
