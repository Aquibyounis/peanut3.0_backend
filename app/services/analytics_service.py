import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import RetrievalAnalytics, SessionAnalytics, AnalyticsSummary

class AnalyticsService:
    def __init__(self):
        self.repo = AnalyticsRepository()

    async def track_event(self, db: AsyncSession, user_id: uuid.UUID | None, session_id: uuid.UUID | None, event_type: str, metadata: dict) -> None:
        await self.repo.create_event(db, user_id, session_id, event_type, metadata)

    async def get_retrieval_stats(self, db: AsyncSession, user_id: uuid.UUID) -> RetrievalAnalytics:
        stats = await self.repo.get_retrieval_analytics(db, user_id)
        return RetrievalAnalytics(**stats)

    async def get_session_stats(self, db: AsyncSession, user_id: uuid.UUID) -> SessionAnalytics:
        stats = await self.repo.get_session_analytics(db, user_id)
        return SessionAnalytics(**stats)

    async def get_summary(self, db: AsyncSession, user_id: uuid.UUID) -> AnalyticsSummary:
        retrieval = await self.get_retrieval_stats(db, user_id)
        sessions = await self.get_session_stats(db, user_id)
        return AnalyticsSummary(retrieval=retrieval, sessions=sessions)
