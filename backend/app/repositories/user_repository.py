from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.base import Repository


class UserRepository(Repository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def by_phone(self, phone: str) -> User | None:
        return self.db.scalar(select(User).where(User.phone == phone))
