import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.memory_repository import MemoryRepository
from app.memory.ltm.qdrant_ltm import QdrantLTM
from app.schemas.memory import MemoryResponse, MemoryStats

class MemoryService:
    def __init__(self):
        self.repo = MemoryRepository()
        self.ltm = QdrantLTM()

    async def store_memory(self, db: AsyncSession, user_id: uuid.UUID, content: str, memory_type: str, importance_score: float = 0.5) -> MemoryResponse:
        qdrant_point_id = await self.ltm.store_memory(str(user_id), content, memory_type, {})
        memory = await self.repo.create_memory(db, user_id, memory_type, content, qdrant_point_id, importance_score)
        return MemoryResponse.model_validate(memory)

    async def search_memories(self, user_id: uuid.UUID, query: str, limit: int = 5, memory_type: str | None = None) -> list[dict]:
        return await self.ltm.search_memories(str(user_id), query, limit, memory_type)

    async def get_memory_stats(self, db: AsyncSession, user_id: uuid.UUID) -> MemoryStats:
        stats = await self.repo.get_memory_stats(db, user_id)
        return MemoryStats(**stats)

    async def delete_memory(self, db: AsyncSession, user_id: uuid.UUID, memory_id: uuid.UUID) -> bool:
        memory = await self.repo.get_memory_by_id(db, memory_id, user_id)
        if not memory:
            return False
            
        if memory.qdrant_point_id:
            await self.ltm.delete_memory(str(user_id), memory.qdrant_point_id)
            
        return await self.repo.delete_memory(db, memory_id, user_id)
