"""
Peanut 3.0 - Kafka Consumer Workers
Concrete consumers for analytics and memory event streams.
"""

from __future__ import annotations

from typing import Any

from app.core.kafka.consumer import BaseKafkaConsumer
from app.core.kafka.topics import KafkaTopics
from app.core.logging.logger import get_logger
from app.core.postgres.database import AsyncSessionLocal
from app.models.analytics import Analytics

logger = get_logger(__name__)


class AnalyticsConsumer(BaseKafkaConsumer):
    """Consumes chat, LLM, and analytics events and persists them."""

    def __init__(self) -> None:
        super().__init__(
            topics=[
                KafkaTopics.CHAT_MESSAGE_SENT,
                KafkaTopics.LLM_RESPONSE_GENERATED,
                KafkaTopics.ANALYTICS_EVENT,
            ],
            group_id="peanut-analytics-consumer",
        )

    async def process_message(self, topic: str, value: dict[str, Any]) -> None:
        logger.info("Analytics event received", topic=topic, payload_keys=list(value.keys()))

        user_id = value.get("user_id")
        session_id = value.get("session_id")
        event_type = topic.rsplit(".", 1)[-1]

        retrieval_latency_ms = value.get("retrieval_latency_ms")
        token_usage = value.get("token_usage")
        reranking_score = value.get("reranking_score")
        memory_hit_rate = value.get("memory_hit_rate")
        semantic_relevance = value.get("semantic_relevance")
        metadata_json = value.get("metadata")

        try:
            async with AsyncSessionLocal() as db:
                import uuid as _uuid

                analytics_record = Analytics(
                    user_id=_uuid.UUID(user_id) if user_id else None,
                    session_id=_uuid.UUID(session_id) if session_id else None,
                    event_type=event_type,
                    retrieval_latency_ms=retrieval_latency_ms,
                    token_usage=token_usage,
                    reranking_score=reranking_score,
                    memory_hit_rate=memory_hit_rate,
                    semantic_relevance=semantic_relevance,
                    metadata_json=metadata_json,
                )
                db.add(analytics_record)
                await db.commit()
                logger.info(
                    "Analytics event persisted",
                    event_type=event_type,
                    record_id=str(analytics_record.id),
                )
        except Exception as exc:
            logger.error("Failed to persist analytics event", error=str(exc), topic=topic)


class MemoryConsumer(BaseKafkaConsumer):
    """Consumes memory-creation events for async processing."""

    def __init__(self) -> None:
        super().__init__(
            topics=[KafkaTopics.MEMORY_CREATED],
            group_id="peanut-memory-consumer",
        )

    async def process_message(self, topic: str, value: dict[str, Any]) -> None:
        logger.info("Memory event received", topic=topic, payload_keys=list(value.keys()))

        user_id = value.get("user_id")
        memory_type = value.get("memory_type", "stm")
        content = value.get("content", "")

        if not user_id or not content:
            logger.warning("Memory event missing required fields", value=value)
            return

        logger.info(
            "Processing memory event",
            user_id=user_id,
            memory_type=memory_type,
            content_length=len(content),
        )

        # Persist memory metadata record
        try:
            async with AsyncSessionLocal() as db:
                import uuid as _uuid

                from app.models.memory import MemoryMetadata

                memory = MemoryMetadata(
                    user_id=_uuid.UUID(user_id),
                    memory_type=memory_type,
                    content=content,
                    metadata_json=value.get("metadata"),
                )
                db.add(memory)
                await db.commit()
                logger.info("Memory event persisted", memory_id=str(memory.id))
        except Exception as exc:
            logger.error("Failed to persist memory event", error=str(exc))
