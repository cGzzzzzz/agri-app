from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class CropBase(BaseModel):
    farm_id: int
    crop_type: str
    crop_variety: str | None = None
    sowing_date: date | None = None
    growth_stage: str | None = None
    irrigation_type: str | None = None
    field_size: str | None = None
    notes: str | None = None


class CropCreate(CropBase):
    pass


class CropUpdate(BaseModel):
    crop_type: str | None = None
    crop_variety: str | None = None
    sowing_date: date | None = None
    growth_stage: str | None = None
    irrigation_type: str | None = None
    field_size: str | None = None
    notes: str | None = None


class CropRead(CropBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime
