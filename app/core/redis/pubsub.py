import json
import asyncio
from typing import AsyncGenerator, Callable, Any
from app.core.redis.client import redis_client
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

async def publish_message(channel: str, message: dict):
    """Publish a message to a Redis channel."""
    try:
        if redis_client.redis:
            await redis_client.redis.publish(channel, json.dumps(message))
            logger.debug(f"Published message to {channel}")
    except Exception as e:
        logger.error(f"Failed to publish to {channel}", error=str(e))

async def subscribe_channel(channel: str) -> AsyncGenerator[dict, None]:
    """Subscribe to a Redis channel and yield messages."""
    if not redis_client.redis:
        logger.error("Redis client not initialized for subscription")
        return
        
    pubsub = redis_client.redis.pubsub()
    try:
        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to {channel}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield data
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode message from {channel}")
    except Exception as e:
        logger.error(f"Subscription error on {channel}", error=str(e))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
