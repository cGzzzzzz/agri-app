from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    farm_id: Mapped[int | None] = mapped_column(ForeignKey("farms.id", ondelete="SET NULL"), nullable=True, index=True)
    crop_id: Mapped[int | None] = mapped_column(ForeignKey("crops.id", ondelete="SET NULL"), nullable=True, index=True)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    action: Mapped[str] = mapped_column(Text)
    urgency: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)
    safety_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    weather_constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="recommendations")
    prediction: Mapped["Prediction"] = relationship(back_populates="recommendations")
