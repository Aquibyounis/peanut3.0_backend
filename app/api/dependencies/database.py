"""
Peanut 3.0 - Database Dependency
Provides async DB session via FastAPI dependency injection.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.postgres.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session, auto-closing when done."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
