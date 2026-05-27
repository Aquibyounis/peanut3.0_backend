"""Pydantic DTOs for the chat and streaming endpoints."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Inbound payload for a chat turn."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user message text.",
    )
    session_id: Optional[uuid.UUID] = Field(
        default=None,
        description=(
            "Existing session to continue. "
            "If omitted a new session is created automatically."
        ),
    )


class ChatMessageResponse(BaseModel):
    """Single message inside a chat history response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    """Non-streaming chat response (kept for backwards compatibility)."""

    response: str
    session_id: uuid.UUID
    follow_up_questions: list[str] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None


class StreamEvent(BaseModel):
    """Individual SSE frame sent during streaming."""

    event: str = Field(
        ...,
        description="Event type: 'token' | 'metadata' | 'follow_up' | 'done' | 'error'",
    )
    data: str


class ChatHistoryResponse(BaseModel):
    """Paginated chat history for a session."""

    messages: list[ChatMessageResponse]
    session_id: uuid.UUID
    has_more: bool
