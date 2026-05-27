"""
Async Kafka consumer base class.

Subclass :class:`BaseKafkaConsumer`, implement :meth:`process_message`, and
call :meth:`run` to start consuming from one or more topics.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from aiokafka import AIOKafkaConsumer, ConsumerRecord

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseKafkaConsumer(ABC):
    """Abstract base for topic consumers."""

    def __init__(
        self,
        topics: list[str],
        group_id: str,
        bootstrap_servers: str = settings.kafka_bootstrap_servers,
    ) -> None:
        self._topics = topics
        self._group_id = group_id
        self._bootstrap_servers = bootstrap_servers
        self._consumer: AIOKafkaConsumer | None = None
        self._running: bool = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Create and start the underlying ``AIOKafkaConsumer``."""
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=self._deserialize_value,
            key_deserializer=self._deserialize_key,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info(
            "Kafka consumer started: topics=%s group=%s",
            self._topics,
            self._group_id,
        )

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        self._running = False
        if self._consumer is not None:
            try:
                await self._consumer.stop()
            except Exception as exc:
                logger.warning("Error stopping Kafka consumer: %s", exc)
            finally:
                self._consumer = None
                logger.info("Kafka consumer stopped.")

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        """
        Blocking coroutine – consumes messages until :meth:`stop` is called.

        Each message is deserialized and handed to :meth:`process_message`.
        Errors in processing are logged but never crash the loop.
        """
        if self._consumer is None:
            raise RuntimeError("Consumer not started. Call start() first.")

        logger.info("Consumer run loop starting for topics=%s", self._topics)
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                try:
                    await self.process_message(
                        topic=msg.topic,
                        key=msg.key,
                        value=msg.value,
                        record=msg,
                    )
                except Exception as exc:
                    logger.error(
                        "Error processing message from %s (offset=%s): %s",
                        msg.topic,
                        msg.offset,
                        exc,
                        exc_info=True,
                    )
        finally:
            await self.stop()

    # ------------------------------------------------------------------ #
    # Abstract hook
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def process_message(
        self,
        topic: str,
        key: str | None,
        value: dict[str, Any],
        record: ConsumerRecord,
    ) -> None:
        """
        Handle a single consumed record.

        Override in subclasses to implement business logic.
        """
        ...

    # ------------------------------------------------------------------ #
    # Serialization helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _deserialize_value(raw: bytes) -> dict[str, Any]:
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Failed to deserialize Kafka value: %s", exc)
            return {"_raw": raw.decode("utf-8", errors="replace")}

    @staticmethod
    def _deserialize_key(raw: bytes | None) -> str | None:
        if raw is None:
            return None
        return raw.decode("utf-8", errors="replace")
