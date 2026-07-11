from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Prediction, User
from app.orchestrator.hierarchical_orchestrator import HierarchicalAgriculturalOrchestrator
from app.schemas.common import ok
from app.services.storage import LocalFileStorage

router = APIRouter(prefix="/disease", tags=["disease"])


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    farm_id: int | None = Form(default=None),
    crop_id: int | None = Form(default=None),
    crop: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image = await LocalFileStorage().save_image(db, current_user.id, file, farm_id)
    result = HierarchicalAgriculturalOrchestrator(db).analyze_image(
        current_user,
        image.storage_path,
        image.id,
        farm_id=farm_id,
        crop_id=crop_id,
        crop_override=crop,
    )
    return ok(result, "Image analyzed")


@router.get("/history")
def scan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(50)
        .all()
    )
    return ok(
        [
            {
                "id": p.id,
                "disease": p.disease_name,
                "confidence": p.disease_confidence,
                "severity": p.severity_label,
                "crop": p.crop_name,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in predictions
        ],
        "Scan history loaded",
    )
