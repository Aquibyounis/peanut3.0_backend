from typing import Optional, List, Dict, Any
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class SupportSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "support_sessions"

    user_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    discord_thread_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    websocket_room_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="open") # open, closed
    last_activity: Mapped[Optional[str]] = mapped_column(String, nullable=True) # ISO format string for simplicity

    messages: Mapped[List["SupportMessage"]] = relationship("SupportMessage", back_populates="session", cascade="all, delete-orphan")


class SupportMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "support_messages"

    session_id: Mapped[str] = mapped_column(ForeignKey("support_sessions.id", ondelete="CASCADE"), index=True)
    sender_type: Mapped[str] = mapped_column(String) # "user", "agent", "system"
    content: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, default={})

    session: Mapped["SupportSession"] = relationship("SupportSession", back_populates="messages")
