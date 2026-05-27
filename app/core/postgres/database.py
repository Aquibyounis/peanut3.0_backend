"""
Peanut 3.0 - Async PostgreSQL Engine & Session

Production: Neon PostgreSQL (serverless) with SSL.
Development: Local PostgreSQL via docker-compose.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Neon serverless requires smaller pools and SSL.
# Local dev is fine with these settings too.
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=3,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "ssl": settings.is_production,
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
