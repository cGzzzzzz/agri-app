from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Conversation, Prediction, Recommendation
from app.repositories.base import Repository


class ConversationRepository(Repository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(Conversation, db)

    def recent_for_user(self, user_id: int, limit: int = 20) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(desc(Conversation.created_at)).limit(limit)
        return list(self.db.scalars(stmt).all())


class PredictionRepository(Repository[Prediction]):
    def __init__(self, db: Session):
        super().__init__(Prediction, db)

    def recent_for_farm(self, farm_id: int | None, user_id: int, limit: int = 10) -> list[Prediction]:
        stmt = select(Prediction).where(Prediction.user_id == user_id)
        if farm_id is not None:
            stmt = stmt.where(Prediction.farm_id == farm_id)
        stmt = stmt.order_by(desc(Prediction.created_at)).limit(limit)
        return list(self.db.scalars(stmt).all())


class RecommendationRepository(Repository[Recommendation]):
    def __init__(self, db: Session):
        super().__init__(Recommendation, db)

    def recent_for_user(self, user_id: int, limit: int = 20) -> list[Recommendation]:
        stmt = select(Recommendation).where(Recommendation.user_id == user_id).order_by(desc(Recommendation.created_at)).limit(limit)
        return list(self.db.scalars(stmt).all())
