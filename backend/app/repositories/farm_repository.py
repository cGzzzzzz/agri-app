from sqlalchemy.orm import Session

from app.models import Farm
from app.repositories.base import Repository


class FarmRepository(Repository[Farm]):
    def __init__(self, db: Session):
        super().__init__(Farm, db)

    def for_user(self, user_id: int) -> list[Farm]:
        return self.list(Farm.user_id == user_id)
