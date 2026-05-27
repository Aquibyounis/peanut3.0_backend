"""Pydantic DTOs for session CRUD endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    """Payload for creating a new chat session."""

    title: str = Field(
        default="New Chat",
        max_length=255,
        description="Human-readable session title.",
    )


class SessionUpdate(BaseModel):
    """Payload for renaming an existing session."""

    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="New session title.",
    )


class SessionResponse(BaseModel):
    """Read-only representation of a session returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""

    sessions: list[SessionResponse]
    total: int
