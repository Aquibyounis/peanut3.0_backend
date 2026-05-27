import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from app.models.memory import MemoryMetadata

class MemoryRepository:
    async def create_memory(self, db: AsyncSession, user_id: uuid.UUID, memory_type: str, content_summary: str, qdrant_point_id: str, importance_score: float) -> MemoryMetadata:
        db_memory = MemoryMetadata(
            id=uuid.uuid4(),
            user_id=user_id,
            memory_type=memory_type,
            content_summary=content_summary,
            qdrant_point_id=qdrant_point_id,
            importance_score=importance_score
        )
        db.add(db_memory)
        await db.commit()
        await db.refresh(db_memory)
        return db_memory

    async def get_user_memories(self, db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[MemoryMetadata]:
        result = await db.execute(select(MemoryMetadata).where(MemoryMetadata.user_id == user_id).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_memory_stats(self, db: AsyncSession, user_id: uuid.UUID) -> dict:
        total_result = await db.execute(select(func.count(MemoryMetadata.id)).where(MemoryMetadata.user_id == user_id))
        total = total_result.scalar_one_or_none() or 0
        
        type_result = await db.execute(select(MemoryMetadata.memory_type, func.count(MemoryMetadata.id)).where(MemoryMetadata.user_id == user_id).group_by(MemoryMetadata.memory_type))
        by_type = {row[0]: row[1] for row in type_result.all()}
        
        avg_imp_result = await db.execute(select(func.avg(MemoryMetadata.importance_score)).where(MemoryMetadata.user_id == user_id))
        avg_importance = avg_imp_result.scalar_one_or_none() or 0.0
        
        return {
            "total_memories": total,
            "by_type": by_type,
            "avg_importance": float(avg_importance)
        }

    async def delete_memory(self, db: AsyncSession, memory_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await db.execute(delete(MemoryMetadata).where(MemoryMetadata.id == memory_id, MemoryMetadata.user_id == user_id))
        await db.commit()
        return result.rowcount > 0

    async def get_memory_by_id(self, db: AsyncSession, memory_id: uuid.UUID, user_id: uuid.UUID) -> MemoryMetadata | None:
        result = await db.execute(select(MemoryMetadata).where(MemoryMetadata.id == memory_id, MemoryMetadata.user_id == user_id))
        return result.scalar_one_or_none()

    async def increment_access_count(self, db: AsyncSession, memory_id: uuid.UUID) -> None:
        await db.execute(update(MemoryMetadata).where(MemoryMetadata.id == memory_id).values(access_count=MemoryMetadata.access_count + 1, last_accessed=func.now()))
        await db.commit()
