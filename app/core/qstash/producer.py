"""
Async QStash producer – fires events via Upstash QStash HTTP API.

Drop-in replacement for the old KafkaProducer.
Gracefully degrades when QStash is unreachable so the rest of the
application keeps running.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.core.qstash.topics import QStashTopics

logger = logging.getLogger(__name__)


class QStashProducer:
    """Async wrapper around Upstash QStash for event publishing."""

    def __init__(self) -> None:
        self._client = None
        self._started: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Initialize the QStash async client."""
        try:
            if not settings.qstash_token:
                logger.warning(
                    "QSTASH_TOKEN not set – events will be dropped"
                )
                return

            from qstash import AsyncQStash
            self._client = AsyncQStash(settings.qstash_token)
            self._started = True
            logger.info("QStash producer started")
        except Exception as exc:
            logger.warning(
                "QStash producer failed to start – events will be dropped: %s",
                exc,
            )
            self._client = None
            self._started = False

    async def stop(self) -> None:
        """Cleanup QStash client."""
        self._client = None
        self._started = False
        logger.info("QStash producer stopped.")

    # ------------------------------------------------------------------ #
    # Core send
    # ------------------------------------------------------------------ #

    async def send_event(
        self,
        topic: str,
        key: str | None = None,
        value: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish a JSON event via QStash.

        The event is delivered as an HTTP POST to the webhook endpoint
        mapped from the topic. If the producer is not connected the event
        is silently dropped with a warning log line.
        """
        if not self._started or self._client is None:
            logger.warning(
                "QStash producer not available – dropping event on topic=%s",
                topic,
            )
            return

        # Resolve the webhook URL for this topic
        webhook_path = QStashTopics.TOPIC_TO_WEBHOOK.get(topic)
        if not webhook_path:
            logger.debug(
                "No webhook mapping for topic=%s – dropping event", topic
            )
            return

        base_url = settings.railway_public_url.rstrip("/")
        destination_url = f"{base_url}{webhook_path}"

        effective_key = key or str(uuid4())
        effective_value = value or {}
        effective_value["_topic"] = topic
        effective_value["_key"] = effective_key

        try:
            res = await self._client.message.publish_json(
                url=destination_url,
                body=effective_value,
            )
            logger.debug(
                "QStash event sent: topic=%s key=%s msg_id=%s",
                topic,
                effective_key,
                res.message_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to send QStash event to %s: %s",
                topic,
                exc,
            )

    # ------------------------------------------------------------------ #
    # Convenience helpers (same interface as old KafkaProducer)
    # ------------------------------------------------------------------ #

    async def send_message_event(
        self,
        chat_id: str,
        message_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=QStashTopics.CHAT_MESSAGE_SENT,
            key=chat_id,
            value=message_data,
        )

    async def send_memory_event(
        self,
        user_id: str,
        memory_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=QStashTopics.MEMORY_CREATED,
            key=user_id,
            value=memory_data,
        )

    async def send_chat_created_event(
        self,
        user_id: str,
        chat_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=QStashTopics.SESSION_CREATED,
            key=user_id,
            value=chat_data,
        )

    async def send_analytics_event(
        self,
        event_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=QStashTopics.ANALYTICS_EVENT,
            value=event_data,
        )

    async def send_user_connected_event(
        self,
        user_id: str,
        connection_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=QStashTopics.USER_REGISTERED,
            key=user_id,
            value=connection_data,
        )

    async def send_llm_response_event(
        self,
        chat_id: str,
        response_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=QStashTopics.LLM_RESPONSE_GENERATED,
            key=chat_id,
            value=response_data,
        )

    async def send_retrieval_event(
        self,
        chat_id: str,
        retrieval_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=QStashTopics.ANALYTICS_EVENT,
            key=chat_id,
            value=retrieval_data,
        )


# Module-level singleton
qstash_producer: QStashProducer = QStashProducer()
