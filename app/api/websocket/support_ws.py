import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
from app.core.redis.pubsub import subscribe_channel
from app.core.logging.logger import get_logger
from typing import Dict, Set

logger = get_logger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # We don't store global websocket state as per requirements.
        # But we need to keep track of active tasks per connection to cleanly shut them down.
        pass

manager = ConnectionManager()

@router.websocket("/ws/support/{room_id}")
async def support_websocket(websocket: WebSocket, room_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected to room {room_id}")
    
    # Task to read from Redis and push to WebSocket
    async def redis_to_ws():
        async for message in subscribe_channel(f"support:{room_id}"):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Failed to send ws message", error=str(e))
                break

    redis_task = asyncio.create_task(redis_to_ws())

    try:
        while True:
            data = await websocket.receive_text()
            # We can handle ping/pong or client-side events here
            # But actual messages should be sent via POST /support/message/send
            # to be persisted in DB first.
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from room {room_id}")
    finally:
        redis_task.cancel()

@router.get("/sse/support/{room_id}")
async def support_sse(request: Request, room_id: str):
    logger.info(f"SSE connected to room {room_id}")
    
    async def event_generator():
        async for message in subscribe_channel(f"support:{room_id}"):
            if await request.is_disconnected():
                break
            yield {
                "event": message.get("event", "message"),
                "data": message
            }

    return EventSourceResponse(event_generator())
