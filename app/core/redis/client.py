"""
Peanut 3.0 - Async Redis Client

Production: Upstash Redis (TLS via rediss:// URLs).
Development: Local Redis via docker-compose.
"""

from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Thin async wrapper around redis.asyncio for lifecycle management."""

    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        # Upstash requires TLS — detect from URL scheme
        use_ssl = settings.redis_url.startswith("rediss://")
        self._client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=10,
            ssl_cert_reqs=None if use_ssl else None,
        )
        await self._client.ping()
        logger.info(
            "Redis connected",
            url=settings.redis_url.split("@")[-1] if "@" in settings.redis_url else settings.redis_url,
            ssl=use_ssl,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis disconnected")

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self._client

    # ── Convenience helpers ──

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> None:
        await self.client.set(key, value, ex=ex)

    async def incr(self, key: str) -> int:
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int) -> None:
        await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def lpush(self, key: str, *values: Any) -> int:
        return await self.client.lpush(key, *values)

    async def llen(self, key: str) -> int:
        return await self.client.llen(key)

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False


redis_client = RedisClient()
