from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: str | None = None
    language: str = "en"


class UserRead(ORMModel):
    id: int
    email: EmailStr
    phone: str | None
    name: str
    language: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    language: str | None = None
