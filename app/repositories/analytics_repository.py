import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.analytics import Analytics
from app.models.session import Session
from app.models.message import Message

class AnalyticsRepository:
    async def create_event(self, db: AsyncSession, user_id: uuid.UUID | None, session_id: uuid.UUID | None, event_type: str, metrics_dict: dict) -> Analytics:
        event = Analytics(
            id=uuid.uuid4(),
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            retrieval_latency_ms=metrics_dict.get('retrieval_latency_ms'),
            token_usage=metrics_dict.get('token_usage'),
            reranking_score=metrics_dict.get('reranking_score'),
            memory_hit_rate=metrics_dict.get('memory_hit_rate'),
            semantic_relevance=metrics_dict.get('semantic_relevance'),
            metadata_json=metrics_dict.get('metadata_json')
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    async def get_retrieval_analytics(self, db: AsyncSession, user_id: uuid.UUID) -> dict:
        result = await db.execute(
            select(
                func.avg(Analytics.retrieval_latency_ms).label('avg_latency'),
                func.count(Analytics.id).label('total'),
                func.avg(Analytics.semantic_relevance).label('avg_relevance'),
                func.avg(Analytics.memory_hit_rate).label('avg_hit_rate')
            ).where(
                and_(
                    Analytics.user_id == user_id,
                    Analytics.event_type == 'retrieval.completed'
                )
            )
        )
        row = result.fetchone()
        
        return {
            "avg_latency_ms": float(row.avg_latency) if row and row.avg_latency else 0.0,
            "total_retrievals": int(row.total) if row and row.total else 0,
            "avg_relevance": float(row.avg_relevance) if row and row.avg_relevance else 0.0,
            "memory_hit_rate": float(row.avg_hit_rate) if row and row.avg_hit_rate else 0.0
        }

    async def get_session_analytics(self, db: AsyncSession, user_id: uuid.UUID) -> dict:
        total_sessions = await db.execute(select(func.count(Session.id)).where(Session.user_id == user_id))
        total_messages = await db.execute(select(func.count(Message.id)).where(Message.user_id == user_id))
        
        t_sessions = total_sessions.scalar_one_or_none() or 0
        t_messages = total_messages.scalar_one_or_none() or 0
        
        return {
            "total_sessions": t_sessions,
            "total_messages": t_messages,
            "avg_messages_per_session": float(t_messages / t_sessions) if t_sessions > 0 else 0.0
        }
