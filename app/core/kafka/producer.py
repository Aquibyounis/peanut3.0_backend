"""
Async Kafka producer – fires events into Kafka topics.

Gracefully degrades when Kafka is unreachable so the rest of the application
keeps running.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Thin async wrapper around :class:`AIOKafkaProducer`."""

    def __init__(self, bootstrap_servers: str = settings.kafka_bootstrap_servers) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None
        self._started: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start the underlying Kafka producer. Logs a warning on failure."""
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            await self._producer.start()
            self._started = True
            logger.info("Kafka producer started (servers=%s)", self._bootstrap_servers)
        except Exception as exc:
            logger.warning(
                "Kafka producer failed to start – events will be dropped: %s",
                exc,
            )
            self._producer = None
            self._started = False

    async def stop(self) -> None:
        """Stop the producer and release resources."""
        if self._producer is not None:
            try:
                await self._producer.stop()
            except Exception as exc:
                logger.warning("Error stopping Kafka producer: %s", exc)
            finally:
                self._producer = None
                self._started = False
                logger.info("Kafka producer stopped.")

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
        Publish a JSON event to *topic*.

        If the producer is not connected the event is silently dropped with a
        warning log line so the caller never crashes.
        """
        if not self._started or self._producer is None:
            logger.warning(
                "Kafka producer not available – dropping event on topic=%s",
                topic,
            )
            return

        effective_key = key or str(uuid4())
        effective_value = value or {}

        try:
            await self._producer.send_and_wait(topic, value=effective_value, key=effective_key)
            logger.debug("Kafka event sent: topic=%s key=%s", topic, effective_key)
        except Exception as exc:
            logger.error(
                "Failed to send Kafka event to %s: %s",
                topic,
                exc,
            )

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #

    async def send_message_event(
        self,
        chat_id: str,
        message_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=KafkaTopics.CHAT_MESSAGE_SENT,
            key=chat_id,
            value=message_data,
        )

    async def send_memory_event(
        self,
        user_id: str,
        memory_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=KafkaTopics.MEMORY_CREATED,
            key=user_id,
            value=memory_data,
        )

    async def send_chat_created_event(
        self,
        user_id: str,
        chat_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=KafkaTopics.CHAT_CREATED,
            key=user_id,
            value=chat_data,
        )

    async def send_analytics_event(
        self,
        event_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=KafkaTopics.ANALYTICS_EVENT,
            value=event_data,
        )

    async def send_user_connected_event(
        self,
        user_id: str,
        connection_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=KafkaTopics.USER_CONNECTED,
            key=user_id,
            value=connection_data,
        )

    async def send_llm_response_event(
        self,
        chat_id: str,
        response_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=KafkaTopics.LLM_RESPONSE_GENERATED,
            key=chat_id,
            value=response_data,
        )

    async def send_retrieval_event(
        self,
        chat_id: str,
        retrieval_data: dict[str, Any],
    ) -> None:
        await self.send_event(
            topic=KafkaTopics.RETRIEVAL_COMPLETED,
            key=chat_id,
            value=retrieval_data,
        )


# Module-level singleton
kafka_producer: KafkaProducer = KafkaProducer()
