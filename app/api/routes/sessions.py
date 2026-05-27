"""Session management REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.models.user import User
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatHistoryResponse, ChatMessageResponse
from app.schemas.session import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])

_session_service = SessionService()
_message_repo = MessageRepository()


# ── POST /sessions ───────────────────────────────────────────────────

@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Start a new chat session for the authenticated user."""
    return await _session_service.create_session(
        db, current_user.id, body.title
    )


# ── GET /sessions ────────────────────────────────────────────────────

@router.get(
    "",
    response_model=SessionListResponse,
    summary="List user sessions",
)
async def list_sessions(
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionListResponse:
    """Return a paginated list of the caller's active sessions."""
    return await _session_service.list_user_sessions(
        db, current_user.id, skip, limit
    )


# ── GET /sessions/{session_id} ──────────────────────────────────────

@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session details",
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Fetch details for a single session owned by the caller."""
    return await _session_service.get_session_detail(
        db, current_user.id, session_id
    )


# ── PATCH /sessions/{session_id} ────────────────────────────────────

@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Rename a session",
)
async def rename_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Rename a session owned by the caller."""
    title = body.title or "New Chat"
    return await _session_service.rename_session(
        db, current_user.id, session_id, title
    )


# ── DELETE /sessions/{session_id} ───────────────────────────────────

@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Hard-delete a session and all its messages."""
    await _session_service.delete_session(
        db, current_user.id, session_id
    )


# ── DELETE /sessions/{session_id}/messages ──────────────────────────

@router.delete(
    "/{session_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear session messages",
)
async def clear_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove all messages from a session without deleting the session."""
    await _session_service.clear_session_messages(
        db, current_user.id, session_id
    )


# ── GET /sessions/{session_id}/history ──────────────────────────────

@router.get(
    "/{session_id}/history",
    response_model=ChatHistoryResponse,
    summary="Get chat history",
)
async def get_chat_history(
    session_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatHistoryResponse:
    """Return paginated chat history for a session owned by the caller."""
    # Verify ownership
    await _session_service.get_session_detail(
        db, current_user.id, session_id
    )

    messages = await _message_repo.get_session_messages(
        db, session_id, skip, limit
    )
    total = await _message_repo.count_session_messages(db, session_id)
    has_more = (skip + limit) < total

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse.model_validate(m) for m in messages
        ],
        session_id=session_id,
        has_more=has_more,
    )
