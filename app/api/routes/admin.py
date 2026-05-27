from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.models.session import Session
from app.repositories.memory_repository import MemoryRepository

router = APIRouter()

# Note: In a real app, you would have an admin role check
@router.get("/sessions")
async def list_all_sessions(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Session))
    return result.scalars().all()

@router.get("/memory/inspect/{user_id}")
async def inspect_user_memory(
    user_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import uuid
    repo = MemoryRepository()
    return await repo.get_user_memories(db, uuid.UUID(user_id))

@router.get("/system/status")
async def system_status(current_user = Depends(get_current_user)):
    return {"status": "ok", "message": "System running optimally."}
