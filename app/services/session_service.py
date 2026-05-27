"""Service layer for session lifecycle management."""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.logger import get_logger
from app.core.redis.client import redis_client
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionListResponse, SessionResponse

logger = get_logger(__name__)


class SessionService:
    """Orchestrates session CRUD, ownership checks, and side-effects."""

    def __init__(self) -> None:
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()

    # ── CREATE ───────────────────────────────────────────────────────

    async def create_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str = "New Chat",
    ) -> SessionResponse:
        """Create a new session for the authenticated user."""
        session = await self.session_repo.create_session(db, user_id, title)
        logger.info(
            "Session created",
            session_id=str(session.id),
            user_id=str(user_id),
        )
        return SessionResponse.model_validate(session)

    # ── LIST ─────────────────────────────────────────────────────────

    async def list_user_sessions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> SessionListResponse:
        """Return a paginated list of the user's active sessions."""
        sessions, total = await self.session_repo.get_user_sessions(
            db, user_id, skip, limit
        )

        # Attach message counts
        session_responses: list[SessionResponse] = []
        for s in sessions:
            count = await self.message_repo.count_session_messages(db, s.id)
            resp = SessionResponse.model_validate(s)
            resp.message_count = count
            session_responses.append(resp)

        return SessionListResponse(sessions=session_responses, total=total)

    # ── DETAIL ───────────────────────────────────────────────────────

    async def get_session_detail(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> SessionResponse:
        """Fetch a single session, verifying the caller owns it."""
        session = await self._get_owned_session(db, user_id, session_id)
        msg_count = await self.message_repo.count_session_messages(
            db, session_id
        )
        resp = SessionResponse.model_validate(session)
        resp.message_count = msg_count
        return resp

    # ── RENAME ───────────────────────────────────────────────────────

    async def rename_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        title: str,
    ) -> SessionResponse:
        """Rename a session owned by the caller."""
        await self._get_owned_session(db, user_id, session_id)
        updated = await self.session_repo.update_session(db, session_id, title)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update session.",
            )
        logger.info(
            "Session renamed",
            session_id=str(session_id),
            new_title=title,
        )
        return SessionResponse.model_validate(updated)

    # ── DELETE ───────────────────────────────────────────────────────

    async def delete_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> bool:
        """Delete a session and purge its STM cache in Redis."""
        await self._get_owned_session(db, user_id, session_id)

        # Clear STM in Redis (best-effort)
        try:
            stm_key = f"stm:{user_id}:{session_id}"
            await redis_client.delete(stm_key)
        except Exception as exc:
            logger.warning(
                "Failed to clear STM from Redis",
                error=str(exc),
                session_id=str(session_id),
            )

        deleted = await self.session_repo.delete_session(db, session_id)
        if deleted:
            logger.info("Session deleted", session_id=str(session_id))
        return deleted

    # ── CLEAR MESSAGES ───────────────────────────────────────────────

    async def clear_session_messages(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> bool:
        """Remove all messages from a session without deleting the session."""
        await self._get_owned_session(db, user_id, session_id)
        count = await self.message_repo.delete_session_messages(db, session_id)
        logger.info(
            "Session messages cleared",
            session_id=str(session_id),
            deleted_count=count,
        )
        return True

    # ── AUTO TITLE ───────────────────────────────────────────────────

    async def auto_generate_title(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        first_message: str,
    ) -> str:
        """Derive a session title from the first user message.

        Uses the first 50 characters, trimmed at the last word boundary
        so the title never truncates mid-word.
        """
        trimmed = first_message[:50].strip()
        if len(first_message) > 50:
            # Cut at last space to avoid breaking a word
            last_space = trimmed.rfind(" ")
            if last_space > 10:
                trimmed = trimmed[:last_space]
            trimmed += "..."

        await self.session_repo.update_session(db, session_id, trimmed)
        logger.info(
            "Auto-generated session title",
            session_id=str(session_id),
            title=trimmed,
        )
        return trimmed

    # ── INTERNAL ─────────────────────────────────────────────────────

    async def _get_owned_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ):
        """Fetch a session and raise 404 / 403 when appropriate."""
        session = await self.session_repo.get_session(db, session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this session.",
            )
        return session
