import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict
from app.api.dependencies.auth import get_current_user
from app.services.chat_service import ChatService
from app.api.dependencies.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_current_user(token, db)
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, session_id)
    chat_service = ChatService()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_data = json.loads(data)
                user_message = msg_data.get("message", "")
                
                if user_message == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))
                    continue

                if user_message:
                    async for chunk in chat_service.process_chat_stream(db, user.id, uuid.UUID(session_id), user_message):
                        # Chunk format is "data: {...}\n\n", extract JSON
                        if chunk.startswith("data: "):
                            raw_json = chunk[6:].strip()
                            await websocket.send_text(raw_json)

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"event": "error", "data": "Invalid JSON"}))

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(session_id)
