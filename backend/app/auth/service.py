from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair
from app.services.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, payload: RegisterRequest) -> tuple[User, TokenPair]:
        if self.users.by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
        if payload.phone and self.users.by_phone(payload.phone):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone is already registered")
        user = User(
            email=payload.email.lower(),
            phone=payload.phone,
            name=payload.name,
            language=payload.language,
            hashed_password=hash_password(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user, self._tokens(user.id)

    def login(self, payload: LoginRequest) -> tuple[User, TokenPair]:
        user = self.users.by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        return user, self._tokens(user.id)

    def refresh(self, refresh_token: str) -> TokenPair:
        user_id = decode_token(refresh_token, "refresh")
        if user_id is None or self.db.get(User, user_id) is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        return self._tokens(user_id)

    def _tokens(self, user_id: int) -> TokenPair:
        return TokenPair(access_token=create_access_token(user_id), refresh_token=create_refresh_token(user_id))
