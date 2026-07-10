from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.service import AuthService
from app.database import get_db
from app.models import User
from app.schemas.auth import AuthPayload, ChangePasswordRequest, LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.common import ok
from app.schemas.user import UserRead
from app.services.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user, tokens = AuthService(db).register(payload)
    return ok(AuthPayload(user=UserRead.model_validate(user), tokens=tokens), "User registered")


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user, tokens = AuthService(db).login(payload)
    return ok(AuthPayload(user=UserRead.model_validate(user), tokens=tokens), "Login successful")


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return ok(AuthService(db).refresh(payload.refresh_token), "Token refreshed")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return ok(UserRead.model_validate(current_user), "Current user")


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, current_user.hashed_password):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return ok(None, "Password changed successfully")
