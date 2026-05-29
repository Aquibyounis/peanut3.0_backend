import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.support import SupportRepository
from app.schemas.support import SupportSessionCreate, SupportMessageCreate, SupportSessionResponse, SupportMessageResponse, SupportSessionWithMessagesResponse
from app.core.redis.pubsub import publish_message
from app.core.logging.logger import get_logger

logger = get_logger(__name__)

class SupportService:
    def __init__(self, db: AsyncSession):
        self.repo = SupportRepository(db)

    async def create_session(self, data: SupportSessionCreate) -> SupportSessionResponse:
        room_id = f"room_{uuid.uuid4().hex[:12]}"
        session = await self.repo.create_session(data, room_id)
        # We will trigger the discord bot via a pubsub event or let the bot listen to a global stream
        # For now, we publish a session_created event
        await publish_message("support:global", {
            "event": "session_created",
            "session_id": str(session.id),
            "user_id": session.user_id,
            "room_id": room_id
        })
        return SupportSessionResponse.model_validate(session)

    async def get_session(self, session_id: uuid.UUID) -> Optional[SupportSessionResponse]:
        session = await self.repo.get_session(session_id)
        if session:
            return SupportSessionResponse.model_validate(session)
        return None

    async def get_session_with_messages(self, session_id: uuid.UUID) -> Optional[SupportSessionWithMessagesResponse]:
        session = await self.repo.get_session_with_messages(session_id)
        if session:
            return SupportSessionWithMessagesResponse.model_validate(session)
        return None

    async def send_message(self, session_id: uuid.UUID, data: SupportMessageCreate) -> SupportMessageResponse:
        message = await self.repo.add_message(session_id, data)
        msg_response = SupportMessageResponse.model_validate(message)
        
        # Publish to room channel for real-time frontend
        session = await self.repo.get_session(session_id)
        if session:
            await publish_message(f"support:{session.websocket_room_id}", {
                "event": "new_message",
                "message": msg_response.model_dump(mode="json")
            })

            # Also publish to global support channel for Discord bot to pick up if sender is 'user'
            if data.sender_type == "user":
                await publish_message("support:discord_outbound", {
                    "event": "user_message",
                    "session_id": str(session_id),
                    "thread_id": session.discord_thread_id,
                    "content": data.content
                })
                
        return msg_response

    async def close_session(self, session_id: uuid.UUID) -> Optional[SupportSessionResponse]:
        session = await self.repo.close_session(session_id)
        if session:
            await publish_message(f"support:{session.websocket_room_id}", {
                "event": "session_closed",
                "session_id": str(session_id)
            })
            return SupportSessionResponse.model_validate(session)
        return None

    async def handle_discord_reply(self, thread_id: str, content: str) -> Optional[SupportMessageResponse]:
        session = await self.repo.get_session_by_thread_id(thread_id)
        if not session:
            return None
        
        # Save message
        data = SupportMessageCreate(sender_type="agent", content=content)
        message = await self.repo.add_message(session.id, data)
        msg_response = SupportMessageResponse.model_validate(message)
        
        # Broadcast to frontend
        await publish_message(f"support:{session.websocket_room_id}", {
            "event": "new_message",
            "message": msg_response.model_dump(mode="json")
        })
        
        return msg_response
