from sqlalchemy.orm import Session

from app.models import Crop, Farm, User
from app.orchestrator.input_types import OrchestratorContext
from app.repositories.history_repository import PredictionRepository
from app.weather.service import WeatherService


class ContextBuilder:
    def __init__(self, db: Session):
        self.db = db
        self.weather = WeatherService()

    def build(
        self, user: User, farm_id: int | None = None, crop_id: int | None = None
    ) -> OrchestratorContext:
        farm = self._farm(user.id, farm_id)
        crop = self._crop(crop_id) if crop_id else self._latest_crop(farm.id if farm else None)
        location = self._location(farm)
        weather = self.weather.current(location)
        history = self._history(user.id, farm.id if farm else None)

        return OrchestratorContext(
            user={"id": user.id, "language": user.language},
            farm=self._farm_dict(farm),
            crop=self._crop_dict(crop),
            weather=weather,
            history=history,
            location=location,
        )

    def _farm(self, user_id: int, farm_id: int | None) -> Farm | None:
        if farm_id is not None:
            farm = self.db.get(Farm, farm_id)
            return farm if farm and farm.user_id == user_id else None
        return (
            self.db.query(Farm)
            .filter(Farm.user_id == user_id)
            .order_by(Farm.created_at.desc())
            .first()
        )

    def _crop(self, crop_id: int) -> Crop | None:
        return self.db.get(Crop, crop_id)

    def _latest_crop(self, farm_id: int | None) -> Crop | None:
        if farm_id is None:
            return None
        return (
            self.db.query(Crop)
            .filter(Crop.farm_id == farm_id)
            .order_by(Crop.created_at.desc())
            .first()
        )

    def _history(self, user_id: int, farm_id: int | None) -> list[dict]:
        predictions = PredictionRepository(self.db).recent_for_farm(farm_id, user_id, 10)
        return [
            {
                "prediction_id": item.id,
                "crop": item.crop_name,
                "disease": item.disease_name,
                "severity": item.severity_label,
                "created_at": item.created_at.isoformat(),
            }
            for item in predictions
        ]

    def _location(self, farm: Farm | None) -> str | None:
        if farm is None:
            return None
        parts = [farm.village, farm.district, farm.state, farm.country]
        return ", ".join(part for part in parts if part)

    def _farm_dict(self, farm: Farm | None) -> dict | None:
        if farm is None:
            return None
        return {
            "id": farm.id,
            "name": farm.name,
            "district": farm.district,
            "state": farm.state,
            "area": farm.area,
            "area_unit": farm.area_unit,
        }

    def _crop_dict(self, crop: Crop | None) -> dict | None:
        if crop is None:
            return None
        return {
            "id": crop.id,
            "farm_id": crop.farm_id,
            "crop_type": crop.crop_type,
            "crop_variety": crop.crop_variety,
            "growth_stage": crop.growth_stage,
            "sowing_date": crop.sowing_date.isoformat() if crop.sowing_date else None,
        }
