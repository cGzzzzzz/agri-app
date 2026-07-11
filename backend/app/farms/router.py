from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Farm, User
from app.repositories.farm_repository import FarmRepository
from app.schemas.common import ok
from app.schemas.farm import FarmCreate, FarmRead, FarmUpdate

router = APIRouter(prefix="/farms", tags=["farms"])


@router.post("")
def create_farm(
    payload: FarmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm = Farm(user_id=current_user.id, **payload.model_dump())
    farm = FarmRepository(db).add(farm)
    return ok(FarmRead.model_validate(farm), "Farm created")


@router.get("")
def list_farms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    farms = FarmRepository(db).for_user(current_user.id)
    return ok([FarmRead.model_validate(farm) for farm in farms], "Farms loaded")


@router.get("/{farm_id}")
def get_farm(
    farm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if farm is None or farm.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return ok(FarmRead.model_validate(farm), "Farm loaded")


@router.patch("/{farm_id}")
def update_farm(
    farm_id: int,
    payload: FarmUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm = db.get(Farm, farm_id)
    if farm is None or farm.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(farm, key, value)
    db.commit()
    db.refresh(farm)
    return ok(FarmRead.model_validate(farm), "Farm updated")


@router.delete("/{farm_id}")
def delete_farm(
    farm_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    farm = db.get(Farm, farm_id)
    if farm is None or farm.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    FarmRepository(db).delete(farm)
    return ok({"id": farm_id}, "Farm deleted")
