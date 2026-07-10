import logging
from datetime import datetime, timedelta, timezone

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
            if (datetime.now(timezone.utc).timestamp() - ts) < self._cache_ttl:
                return data
        return None

    def _set_cached(self, key: str, data: dict) -> None:
        self._cache[key] = (datetime.now(timezone.utc).timestamp(), data)

    def _geocode(self, location: str) -> tuple[float, float] | None:
        cache_key = f"geo:{location}"
        cached = self._get_cached(cache_key)
        if cached:
            return (cached["lat"], cached["lon"])

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(GEOCODE_URL, params={"name": location, "count": 1, "language": "en"})
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
            return self._fallback_current(location)

        lat, lon = coords
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(WEATHER_URL, params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
                    "timezone": "auto",
                })
                resp.raise_for_status()
                data = resp.json()
                current = data.get("current", {})

                temp = current.get("temperature_2m", 31.0)
                humidity = current.get("relative_humidity_2m", 80)
                rain_prob = current.get("precipitation_probability", 50)
                wind = current.get("wind_speed_10m", 10.0)
                weather_code = current.get("weather_code", 0)

                condition = self._decode_weather_code(weather_code)
                advisory = self._generate_advisory(temp, humidity, rain_prob, condition)

                result = {
                    "location": location or "Unknown",
                    "temperature_c": temp,
                    "condition": condition,
                    "humidity_percent": humidity,
                    "precipitation_probability_percent": rain_prob,
                    "wind_kph": wind,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "advisory": advisory,
                    "source": "open-meteo",
                }
                self._set_cached(cache_key, result)
                return result
        except Exception:
            logger.warning("Open-Meteo API failed, using fallback", exc_info=True)
            return self._fallback_current(location)

    def forecast(self, location: str | None = None, days: int = 5) -> dict:
        cache_key = f"forecast:{location}:{days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        coords = self._geocode(location or "Tamil Nadu, India")
        if coords is None:
            return self._fallback_forecast(location, days)

        lat, lon = coords
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(WEATHER_URL, params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                    "timezone": "auto",
                    "forecast_days": days,
                })
                resp.raise_for_status()
                data = resp.json()
                daily = data.get("daily", {})

                forecast_days = []
                dates = daily.get("time", [])
                for i, date in enumerate(dates):
                    rain = daily.get("precipitation_probability_max", [0] * days)[i] if i < len(daily.get("precipitation_probability_max", [])) else 0
                    tmax = daily.get("temperature_2m_max", [32] * days)[i] if i < len(daily.get("temperature_2m_max", [])) else 32
                    tmin = daily.get("temperature_2m_min", [24] * days)[i] if i < len(daily.get("temperature_2m_min", [])) else 24
                    wcode = daily.get("weather_code", [0] * days)[i] if i < len(daily.get("weather_code", [])) else 0

                    condition = self._decode_weather_code(wcode)
                    forecast_days.append({
                        "date": date,
                        "condition": condition,
                        "min_temp_c": tmin,
                        "max_temp_c": tmax,
                        "rain_probability_percent": rain,
                        "advisory": "Delay foliar spray" if rain >= 50 else "Suitable spray window possible",
                    })

                result = {"location": location or "Unknown", "days": forecast_days, "source": "open-meteo"}
                self._set_cached(cache_key, result)
                return result
        except Exception:
            logger.warning("Open-Meteo forecast failed", exc_info=True)
            return self._fallback_forecast(location, days)

    def _decode_weather_code(self, code: int) -> str:
        codes = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
        }
        return codes.get(code, f"Weather code {code}")

    def _generate_advisory(self, temp: float, humidity: float, rain_prob: float, condition: str) -> str:
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

    def _fallback_current(self, location: str | None) -> dict:
        return {
            "location": location or "Local Farm",
            "temperature_c": 31.0,
            "condition": "Humid with possible rain",
            "humidity_percent": 84,
            "precipitation_probability_percent": 68,
            "wind_kph": 9.0,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "advisory": "Disease pressure is elevated; avoid spraying during rain windows.",
            "source": "fallback",
        }

    def _fallback_forecast(self, location: str | None, days: int) -> dict:
        start = datetime.now(timezone.utc).date()
        forecast_days = []
        for index in range(days):
            rain = max(20, 70 - index * 8)
            forecast_days.append({
                "date": str(start + timedelta(days=index)),
                "condition": "Rain likely" if rain >= 50 else "Partly cloudy",
                "min_temp_c": 24.0,
                "max_temp_c": 32.0,
                "rain_probability_percent": rain,
                "advisory": "Delay foliar spray" if rain >= 50 else "Suitable spray window possible",
            })
        return {"location": location or "Local Farm", "days": forecast_days, "source": "fallback"}
