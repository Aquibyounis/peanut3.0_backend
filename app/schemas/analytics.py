from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AnalyticsEvent(BaseModel):
    event_type: str
    metadata: Optional[dict] = None

class AnalyticsQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: Optional[str] = None

class RetrievalAnalytics(BaseModel):
    avg_latency_ms: float
    total_retrievals: int
    avg_relevance: float
    memory_hit_rate: float

class SessionAnalytics(BaseModel):
    total_sessions: int
    total_messages: int
    avg_messages_per_session: float

class AnalyticsSummary(BaseModel):
    retrieval: RetrievalAnalytics
    sessions: SessionAnalytics
