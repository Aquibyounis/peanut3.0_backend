from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

class SupportMessageBase(BaseModel):
    sender_type: str = Field(..., description="user, agent, or system")
    content: str
    metadata_json: Optional[Dict[str, Any]] = None

class SupportMessageCreate(SupportMessageBase):
    pass

class SupportMessageResponse(SupportMessageBase):
    id: UUID
    session_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportSessionBase(BaseModel):
    user_id: Optional[str] = None
    status: str = "open"

class SupportSessionCreate(SupportSessionBase):
    pass

class SupportSessionResponse(SupportSessionBase):
    id: UUID
    discord_thread_id: Optional[str] = None
    websocket_room_id: str
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SupportSessionWithMessagesResponse(SupportSessionResponse):
    messages: List[SupportMessageResponse] = []
