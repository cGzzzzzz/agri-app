from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], db: Session):
        self.model = model
        self.db = db

    def get(self, obj_id: int) -> ModelT | None:
        return self.db.get(self.model, obj_id)

    def list(self, *filters: Any) -> list[ModelT]:
        stmt = select(self.model)
        for clause in filters:
            stmt = stmt.where(clause)
        return list(self.db.scalars(stmt).all())

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.commit()
