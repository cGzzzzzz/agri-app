from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Crop, Farm, User
from app.repositories.crop_repository import CropRepository
from app.schemas.common import ok
from app.schemas.crop import CropCreate, CropRead, CropUpdate

router = APIRouter(prefix="/crops", tags=["crops"])


def _assert_farm_owner(db: Session, farm_id: int, user_id: int) -> None:
    farm = db.get(Farm, farm_id)
    if farm is None or farm.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")


@router.post("")
def create_crop(
    payload: CropCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_farm_owner(db, payload.farm_id, current_user.id)
    crop = Crop(**payload.model_dump())
    crop = CropRepository(db).add(crop)
    return ok(CropRead.model_validate(crop), "Crop created")


@router.get("")
def list_crops(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    crops = CropRepository(db).for_user(current_user.id)
    return ok([CropRead.model_validate(crop) for crop in crops], "Crops loaded")


@router.get("/{crop_id}")
def get_crop(
    crop_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    _assert_farm_owner(db, crop.farm_id, current_user.id)
    return ok(CropRead.model_validate(crop), "Crop loaded")


@router.patch("/{crop_id}")
def update_crop(
    crop_id: int,
    payload: CropUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    _assert_farm_owner(db, crop.farm_id, current_user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(crop, key, value)
    db.commit()
    db.refresh(crop)
    return ok(CropRead.model_validate(crop), "Crop updated")


@router.delete("/{crop_id}")
def delete_crop(
    crop_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    _assert_farm_owner(db, crop.farm_id, current_user.id)
    CropRepository(db).delete(crop)
    return ok({"id": crop_id}, "Crop deleted")
