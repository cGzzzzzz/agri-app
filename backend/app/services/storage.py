from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ImageAsset


class LocalFileStorage:
    def __init__(self):
        settings = get_settings()
        self.root = Path(settings.storage_dir)
        self.image_dir = self.root / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)

    async def save_image(
        self, db: Session, user_id: int, file: UploadFile, farm_id: int | None = None
    ) -> ImageAsset:
        suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
        filename = f"{uuid4().hex}{suffix.lower()}"
        storage_path = self.image_dir / filename
        content = await file.read()
        storage_path.write_bytes(content)
        image = ImageAsset(
            user_id=user_id,
            farm_id=farm_id,
            original_filename=file.filename or filename,
            storage_path=str(storage_path.as_posix()),
            content_type=file.content_type,
            size_bytes=len(content),
        )
        db.add(image)
        db.commit()
        db.refresh(image)
        return image
