"""
Central model registry – import every model here so Alembic auto-generates
migrations for all tables.
"""

from app.models.base import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.session import Session  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.analytics import Analytics  # noqa: F401
from app.models.memory import MemoryMetadata  # noqa: F401
