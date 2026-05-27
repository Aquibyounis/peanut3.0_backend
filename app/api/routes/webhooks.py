"""
Peanut 3.0 - QStash Webhook Endpoints

Receives async event callbacks from Upstash QStash.
Replaces the old Kafka consumer workers.
"""

from __future__ import annotations

import json
import uuid as _uuid
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from app.core.config import settings
from app.core.logging.logger import get_logger
from app.core.postgres.database import AsyncSessionLocal
from app.models.analytics import Analytics

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_qstash_signature(request: Request, body: bytes) -> bool:
    """
    Verify QStash webhook signature using the Receiver class.
    Returns True if valid or if signing keys are not configured (dev mode).
    """
    if not settings.qstash_current_signing_key:
        # Dev mode – no verification
        return True

    try:
        from qstash import Receiver

        receiver = Receiver(
            current_signing_key=settings.qstash_current_signing_key,
            next_signing_key=settings.qstash_next_signing_key,
        )
        signature = request.headers.get("Upstash-Signature", "")
        receiver.verify(
            body=body.decode("utf-8"),
            signature=signature,
            url=str(request.url),
        )
        return True
    except Exception as exc:
        logger.warning("QStash signature verification failed", error=str(exc))
        return False


@router.post("/analytics")
async def webhook_analytics(request: Request):
    """
    Receives analytics events (chat messages, LLM responses, generic analytics).
    Same business logic as the old AnalyticsConsumer.
    """
    body = await request.body()

    if not _verify_qstash_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid QStash signature")

    try:
        value: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    topic = value.get("_topic", "unknown")
    logger.info("Analytics webhook received", topic=topic, payload_keys=list(value.keys()))

    user_id = value.get("user_id")
    session_id = value.get("session_id")
    event_type = topic.rsplit(".", 1)[-1] if "." in topic else topic

    retrieval_latency_ms = value.get("retrieval_latency_ms")
    token_usage = value.get("token_usage")
    reranking_score = value.get("reranking_score")
    memory_hit_rate = value.get("memory_hit_rate")
    semantic_relevance = value.get("semantic_relevance")
    metadata_json = value.get("metadata")

    try:
        async with AsyncSessionLocal() as db:
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

    return {"status": "ok"}


@router.post("/memory")
async def webhook_memory(request: Request):
    """
    Receives memory creation events for async processing.
    Same business logic as the old MemoryConsumer.
    """
    body = await request.body()

    if not _verify_qstash_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid QStash signature")

    try:
        value: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    topic = value.get("_topic", "unknown")
    logger.info("Memory webhook received", topic=topic, payload_keys=list(value.keys()))

    user_id = value.get("user_id")
    memory_type = value.get("memory_type", "stm")
    content = value.get("content", "")

    if not user_id or not content:
        logger.warning("Memory event missing required fields", value=value)
        return {"status": "skipped", "reason": "missing fields"}

    logger.info(
        "Processing memory event",
        user_id=user_id,
        memory_type=memory_type,
        content_length=len(content),
    )

    try:
        async with AsyncSessionLocal() as db:
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

    return {"status": "ok"}
