from pydantic import BaseModel, EmailStr

from app.schemas.user import UserCreate, UserRead


class RegisterRequest(UserCreate):
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AuthPayload(BaseModel):
    user: UserRead
    tokens: TokenPair
