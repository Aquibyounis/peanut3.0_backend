"""
Redis-based Short-Term Memory (STM).

Stores recent conversation turns per user/session in Redis lists with TTL.
Provides context window retrieval with token budgeting and conversation
summary storage for compressed context.
"""

import json
from typing import Optional

from app.core.redis.client import redis_client
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class RedisSTM:
    """Short-Term Memory using Redis."""

    DEFAULT_TTL: int = 1800  # 30 minutes
    MAX_MESSAGES: int = 20

    def _key(self, user_id: str, session_id: str) -> str:
        return f"stm:{user_id}:{session_id}"

    def _summary_key(self, user_id: str, session_id: str) -> str:
        return f"stm:summary:{user_id}:{session_id}"

    async def store_message(
        self, user_id: str, session_id: str, role: str, content: str
    ) -> None:
        """Store a message in STM with TTL."""
        key = self._key(user_id, session_id)
        message = json.dumps({"role": role, "content": content})
        await redis_client.lpush(key, message)
        await redis_client.ltrim(key, 0, self.MAX_MESSAGES - 1)
        # Reset TTL on each new message
        if redis_client._redis:
            await redis_client._redis.expire(key, self.DEFAULT_TTL)
        logger.debug(
            "STM message stored",
            user_id=user_id,
            session_id=session_id,
            role=role,
        )

    async def get_recent_messages(
        self, user_id: str, session_id: str, limit: int = 10
    ) -> list[dict]:
        """Get recent messages from STM."""
        key = self._key(user_id, session_id)
        raw_messages = await redis_client.lrange(key, 0, limit - 1)
        messages: list[dict] = []
        for raw in reversed(raw_messages):  # Reverse to get chronological order
            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                messages.append(json.loads(raw))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        return messages

    async def get_context_window(
        self, user_id: str, session_id: str, max_tokens: int = 2000
    ) -> str:
        """Get formatted context window from STM, respecting token budget."""
        messages = await self.get_recent_messages(
            user_id, session_id, limit=self.MAX_MESSAGES
        )
        if not messages:
            return ""

        context_parts: list[str] = []
        estimated_tokens: float = 0.0

        for msg in messages:
            msg_text = f"{msg['role'].upper()}: {msg['content']}"
            msg_tokens = len(msg_text.split()) * 1.3  # rough estimate
            if estimated_tokens + msg_tokens > max_tokens:
                break
            context_parts.append(msg_text)
            estimated_tokens += msg_tokens

        return "\n".join(context_parts)

    async def store_summary(
        self, user_id: str, session_id: str, summary: str
    ) -> None:
        """Store a compressed summary of the conversation."""
        key = self._summary_key(user_id, session_id)
        await redis_client.setex(key, self.DEFAULT_TTL * 2, summary)

    async def get_summary(
        self, user_id: str, session_id: str
    ) -> Optional[str]:
        """Get the conversation summary."""
        key = self._summary_key(user_id, session_id)
        return await redis_client.get(key)

    async def clear(self, user_id: str, session_id: str) -> None:
        """Clear STM for a session."""
        await redis_client.delete(self._key(user_id, session_id))
        await redis_client.delete(self._summary_key(user_id, session_id))
        logger.info("STM cleared", user_id=user_id, session_id=session_id)
