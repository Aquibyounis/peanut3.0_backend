"""
Session utilities – async context managers for database sessions and transactions.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.postgres.database import AsyncSessionLocal


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that provides an ``AsyncSession``.

    Usage::

        async with get_session() as session:
            result = await session.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that wraps the session in an explicit transaction.

    Commits on successful exit, rolls back on exception.

    Usage::

        async with transaction() as session:
            session.add(new_user)
            # auto-committed on block exit
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
