from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.weather.service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current")
def current(location: str | None = Query(default=None)):
    return ok(WeatherService().current(location), "Current weather loaded")


@router.get("/forecast")
def forecast(location: str | None = Query(default=None), days: int = Query(default=5, ge=1, le=10)):
    return ok(WeatherService().forecast(location, days), "Forecast loaded")
