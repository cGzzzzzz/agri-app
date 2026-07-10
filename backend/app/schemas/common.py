from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = ""
    data: T | None = None


def ok(data=None, message: str = "") -> dict:
    return {"success": True, "message": message, "data": data}


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
