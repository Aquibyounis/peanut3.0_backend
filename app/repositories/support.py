from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.support import SupportSession, SupportMessage
from app.schemas.support import SupportSessionCreate, SupportMessageCreate

class SupportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, data: SupportSessionCreate, websocket_room_id: str) -> SupportSession:
        db_session = SupportSession(
            user_id=data.user_id,
            status=data.status,
            websocket_room_id=websocket_room_id
        )
        self.session.add(db_session)
        await self.session.commit()
        await self.session.refresh(db_session)
        return db_session

    async def get_session(self, session_id: UUID) -> Optional[SupportSession]:
        stmt = select(SupportSession).where(SupportSession.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_by_thread_id(self, thread_id: str) -> Optional[SupportSession]:
        stmt = select(SupportSession).where(SupportSession.discord_thread_id == thread_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_with_messages(self, session_id: UUID) -> Optional[SupportSession]:
        stmt = select(SupportSession).options(selectinload(SupportSession.messages)).where(SupportSession.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_session_thread(self, session_id: UUID, thread_id: str) -> Optional[SupportSession]:
        db_session = await self.get_session(session_id)
        if db_session:
            db_session.discord_thread_id = thread_id
            await self.session.commit()
            await self.session.refresh(db_session)
        return db_session

    async def close_session(self, session_id: UUID) -> Optional[SupportSession]:
        db_session = await self.get_session(session_id)
        if db_session:
            db_session.status = "closed"
            await self.session.commit()
            await self.session.refresh(db_session)
        return db_session

    async def add_message(self, session_id: UUID, data: SupportMessageCreate) -> SupportMessage:
        message = SupportMessage(
            session_id=session_id,
            sender_type=data.sender_type,
            content=data.content,
            metadata_json=data.metadata_json
        )
        self.session.add(message)
        
        # Update last activity
        db_session = await self.get_session(session_id)
        if db_session:
            db_session.last_activity = message.created_at.isoformat() if message.created_at else None

        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages(self, session_id: UUID) -> List[SupportMessage]:
        stmt = select(SupportMessage).where(SupportMessage.session_id == session_id).order_by(SupportMessage.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
