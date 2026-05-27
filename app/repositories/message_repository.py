"""Repository layer for Message CRUD operations."""

import uuid
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    """Thin data-access wrapper around the ``messages`` table."""

    # ── CREATE ───────────────────────────────────────────────────────

    async def create_message(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        content: str,
        metadata_json: Optional[dict[str, Any]] = None,
        token_count: Optional[int] = None,
    ) -> Message:
        """Persist a new message and return the ORM instance."""
        message = Message(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
            token_count=token_count,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    # ── READ ─────────────────────────────────────────────────────────

    async def get_session_messages(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Message]:
        """Return a page of messages for a session ordered chronologically."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        limit: int = 10,
    ) -> list[Message]:
        """Return the *N* most recent messages in chronological order.

        The query fetches the newest ``limit`` rows (DESC), then reverses
        so callers always receive oldest-first ordering.
        """
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    # ── AGGREGATES ───────────────────────────────────────────────────

    async def count_session_messages(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> int:
        """Return the total number of messages in a session."""
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    # ── DELETE ───────────────────────────────────────────────────────

    async def delete_session_messages(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> int:
        """Remove all messages for a session.

        Returns the number of deleted rows.
        """
        stmt = (
            delete(Message)
            .where(Message.session_id == session_id)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount  # type: ignore[return-value]
