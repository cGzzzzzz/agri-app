from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class FarmBase(BaseModel):
    name: str
    village: str | None = None
    district: str | None = None
    state: str | None = None
    country: str = "India"
    area: float | None = None
    area_unit: str = "acre"
    latitude: float | None = None
    longitude: float | None = None


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    name: str | None = None
    village: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = None
    area: float | None = None
    area_unit: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class FarmRead(FarmBase, ORMModel):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
