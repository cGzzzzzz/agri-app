from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    farm_id: Mapped[int | None] = mapped_column(
        ForeignKey("farms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    crop_id: Mapped[int | None] = mapped_column(
        ForeignKey("crops.id", ondelete="SET NULL"), nullable=True, index=True
    )
    image_id: Mapped[int | None] = mapped_column(
        ForeignKey("images.id", ondelete="SET NULL"), nullable=True, index=True
    )
    crop_name: Mapped[str] = mapped_column(String(120))
    crop_confidence: Mapped[float] = mapped_column(Float)
    disease_name: Mapped[str] = mapped_column(String(160))
    disease_confidence: Mapped[float] = mapped_column(Float)
    severity_label: Mapped[str] = mapped_column(String(80))
    severity_score: Mapped[float] = mapped_column(Float)
    xai_summary: Mapped[str] = mapped_column(Text)
    model_trace: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farm: Mapped["Farm"] = relationship(back_populates="predictions")
    crop: Mapped["Crop"] = relationship(back_populates="predictions")
    image: Mapped["ImageAsset"] = relationship(back_populates="predictions")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="prediction")
