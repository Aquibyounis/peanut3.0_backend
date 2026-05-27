from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import RetrievalAnalytics, SessionAnalytics, AnalyticsSummary

router = APIRouter()

@router.get("/retrieval", response_model=RetrievalAnalytics)
async def get_retrieval_analytics(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AnalyticsService()
    return await service.get_retrieval_stats(db, current_user.id)

@router.get("/sessions", response_model=SessionAnalytics)
async def get_session_analytics(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AnalyticsService()
    return await service.get_session_stats(db, current_user.id)

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AnalyticsService()
    return await service.get_summary(db, current_user.id)
