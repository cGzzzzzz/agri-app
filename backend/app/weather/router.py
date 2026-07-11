from fastapi import APIRouter, Query

from app.schemas.common import ok
from app.weather.service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current")
def current(
    location: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
):
    if lat is not None and lng is not None:
        return ok(WeatherService().current_by_coords(lat, lng), "Current weather loaded")
    return ok(WeatherService().current(location), "Current weather loaded")


@router.get("/forecast")
def forecast(location: str | None = Query(default=None), days: int = Query(default=5, ge=1, le=10)):
    return ok(WeatherService().forecast(location, days), "Forecast loaded")
