"""
Peanut 3.0 - Analytics Worker
Background tasks for aggregating session stats and computing retrieval metrics.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.logger import get_logger
from app.core.postgres.database import AsyncSessionLocal
from app.models.analytics import Analytics
from app.models.message import Message
from app.models.session import Session

logger = get_logger(__name__)


async def aggregate_session_stats() -> dict[str, Any]:
    """
    Aggregate session-level statistics across all users.

    Returns
    -------
    dict with total_sessions, total_messages, avg_messages_per_session.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Total sessions
            total_sessions_result = await db.execute(select(func.count(Session.id)))
            total_sessions: int = total_sessions_result.scalar() or 0

            # Total messages
            total_messages_result = await db.execute(select(func.count(Message.id)))
            total_messages: int = total_messages_result.scalar() or 0

            # Avg messages per session
            if total_sessions > 0:
                avg_messages = round(total_messages / total_sessions, 2)
            else:
                avg_messages = 0.0

            # Sessions per day (last 30 days)
            from datetime import datetime, timedelta, timezone

            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent_sessions_result = await db.execute(
                select(func.count(Session.id)).where(Session.created_at >= thirty_days_ago)
            )
            recent_sessions: int = recent_sessions_result.scalar() or 0
            daily_avg = round(recent_sessions / 30, 2)

            stats = {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": avg_messages,
                "sessions_last_30_days": recent_sessions,
                "daily_avg_sessions": daily_avg,
            }
            logger.info("Session stats aggregated", **stats)
            return stats

    except Exception as exc:
        logger.error("Session stats aggregation failed", error=str(exc))
        return {
            "total_sessions": 0,
            "total_messages": 0,
            "avg_messages_per_session": 0.0,
            "error": str(exc),
        }


async def compute_retrieval_metrics() -> dict[str, Any]:
    """
    Compute retrieval quality metrics from analytics records.

    Returns
    -------
    dict with avg_latency_ms, total_retrievals, avg_relevance, memory_hit_rate.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Total retrieval events
            total_result = await db.execute(
                select(func.count(Analytics.id)).where(
                    Analytics.retrieval_latency_ms.isnot(None)
                )
            )
            total_retrievals: int = total_result.scalar() or 0

            if total_retrievals == 0:
                return {
                    "avg_latency_ms": 0.0,
                    "total_retrievals": 0,
                    "avg_relevance": 0.0,
                    "memory_hit_rate": 0.0,
                }

            # Avg latency
            avg_latency_result = await db.execute(
                select(func.avg(Analytics.retrieval_latency_ms)).where(
                    Analytics.retrieval_latency_ms.isnot(None)
                )
            )
            avg_latency: float = round(float(avg_latency_result.scalar() or 0.0), 2)

            # Avg relevance
            avg_relevance_result = await db.execute(
                select(func.avg(Analytics.semantic_relevance)).where(
                    Analytics.semantic_relevance.isnot(None)
                )
            )
            avg_relevance: float = round(float(avg_relevance_result.scalar() or 0.0), 4)

            # Memory hit rate (average of non-null memory_hit_rate values)
            hit_rate_result = await db.execute(
                select(func.avg(Analytics.memory_hit_rate)).where(
                    Analytics.memory_hit_rate.isnot(None)
                )
            )
            memory_hit_rate: float = round(float(hit_rate_result.scalar() or 0.0), 4)

            metrics = {
                "avg_latency_ms": avg_latency,
                "total_retrievals": total_retrievals,
                "avg_relevance": avg_relevance,
                "memory_hit_rate": memory_hit_rate,
            }
            logger.info("Retrieval metrics computed", **metrics)
            return metrics

    except Exception as exc:
        logger.error("Retrieval metrics computation failed", error=str(exc))
        return {
            "avg_latency_ms": 0.0,
            "total_retrievals": 0,
            "avg_relevance": 0.0,
            "memory_hit_rate": 0.0,
            "error": str(exc),
        }
