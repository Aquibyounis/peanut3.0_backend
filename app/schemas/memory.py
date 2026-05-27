from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict
from datetime import datetime
import uuid

class MemoryCreate(BaseModel):
    content: str
    memory_type: str
    importance_score: float = 0.5

class MemoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    memory_type: str
    content_summary: str
    importance_score: float
    access_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 5
    memory_type: Optional[str] = None

class MemorySearchResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int

class MemoryStats(BaseModel):
    total_memories: int
    by_type: Dict[str, int]
    avg_importance: float
