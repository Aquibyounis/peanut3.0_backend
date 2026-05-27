"""
Peanut 3.0 - Memory Router
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.models.memory import MemoryMetadata
from app.models.user import User

router = APIRouter(prefix="/memory", tags=["Memory"])


# ── Schemas ──

class MemoryCreate(BaseModel):
    memory_type: str  # "stm" | "ltm"
    content: str
    metadata: dict | None = None


class MemoryResponse(BaseModel):
    id: uuid.UUID
    memory_type: str
    content: str
    relevance_score: float | None
    metadata_json: dict | None

    model_config = {"from_attributes": True}


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int


# ── Endpoints ──

@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    req: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemoryResponse:
    memory = MemoryMetadata(
        user_id=current_user.id,
        memory_type=req.memory_type,
        content=req.content,
        metadata_json=req.metadata,
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return MemoryResponse.model_validate(memory)


@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    memory_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemoryListResponse:
    stmt = select(MemoryMetadata).where(MemoryMetadata.user_id == current_user.id)
    if memory_type:
        stmt = stmt.where(MemoryMetadata.memory_type == memory_type)
    stmt = stmt.order_by(MemoryMetadata.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    memories = result.scalars().all()
    return MemoryListResponse(
        memories=[MemoryResponse.model_validate(m) for m in memories],
        total=len(memories),
    )


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(MemoryMetadata).where(
            MemoryMetadata.id == memory_id, MemoryMetadata.user_id == current_user.id
        )
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    await db.delete(memory)
    await db.commit()
