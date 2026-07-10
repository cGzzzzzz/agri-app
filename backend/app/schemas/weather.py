from datetime import datetime

from pydantic import BaseModel


class WeatherRead(BaseModel):
    location: str
    temperature_c: float
    condition: str
    humidity_percent: int
    precipitation_probability_percent: int
    wind_kph: float
    observed_at: datetime
    advisory: str


class ForecastDay(BaseModel):
    date: str
    condition: str
    min_temp_c: float
    max_temp_c: float
    rain_probability_percent: int
    advisory: str


class ForecastRead(BaseModel):
    location: str
    days: list[ForecastDay]
