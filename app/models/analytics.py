import uuid
from sqlalchemy import Column, String, Float, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class Analytics(Base, TimestampMixin):
    __tablename__ = 'analytics'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id'), index=True, nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('sessions.id'), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    retrieval_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reranking_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_hit_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Relationships
    user = relationship("User", backref="analytics_events")
    session = relationship("Session", backref="analytics_events")
