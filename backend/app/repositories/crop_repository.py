from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Crop, Farm
from app.repositories.base import Repository


class CropRepository(Repository[Crop]):
    def __init__(self, db: Session):
        super().__init__(Crop, db)

    def for_user(self, user_id: int) -> list[Crop]:
        stmt = select(Crop).join(Farm).where(Farm.user_id == user_id)
        return list(self.db.scalars(stmt).all())
