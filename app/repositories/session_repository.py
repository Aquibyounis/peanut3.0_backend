"""Repository layer for Session CRUD operations."""

import uuid
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionRepository:
    """Thin data-access wrapper around the ``sessions`` table."""

    # ── CREATE ───────────────────────────────────────────────────────

    async def create_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str = "New Chat",
    ) -> Session:
        """Insert a new session row and return the ORM instance."""
        session = Session(user_id=user_id, title=title)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    # ── READ ─────────────────────────────────────────────────────────

    async def get_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> Optional[Session]:
        """Fetch a single session by primary key (or ``None``)."""
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Session], int]:
        """Return a page of sessions for a user together with the total count.

        Sessions are ordered newest-first.
        """
        # total count
        count_stmt = (
            select(func.count())
            .select_from(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
        )
        total_result = await db.execute(count_stmt)
        total: int = total_result.scalar_one()

        # paginated rows
        rows_stmt = (
            select(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
            .order_by(Session.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows_result = await db.execute(rows_stmt)
        sessions = list(rows_result.scalars().all())

        return sessions, total

    # ── UPDATE ───────────────────────────────────────────────────────

    async def update_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        title: str,
    ) -> Optional[Session]:
        """Rename a session. Returns the refreshed ORM instance or ``None``."""
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(title=title)
            .returning(Session.id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        await db.commit()
        return await self.get_session(db, session_id)

    # ── DELETE ───────────────────────────────────────────────────────

    async def delete_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> bool:
        """Hard-delete a session and cascade to its messages.

        Returns ``True`` if a row was actually removed.
        """
        session = await self.get_session(db, session_id)
        if session is None:
            return False
        await db.delete(session)
        await db.commit()
        return True

    # ── HELPERS ──────────────────────────────────────────────────────

    async def count_user_sessions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """Return the number of active sessions for a user."""
        stmt = (
            select(func.count())
            .select_from(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
        )
        result = await db.execute(stmt)
        return result.scalar_one()
