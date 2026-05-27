"""
User repository – async CRUD operations against the ``users`` table.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security.hashing import hash_password
from app.schemas.auth import UserRegister


async def create_user(db: AsyncSession, user_data: UserRegister) -> User:
    """
    Insert a new user row.

    The plain-text password from *user_data* is hashed before storage.
    """
    user = User(
        id=uuid.uuid4(),
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Look up a user by their email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    """Look up a user by their UUID."""
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Look up a user by their username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def update_user(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    update_data: dict[str, Any],
) -> User:
    """
    Update one or more columns on an existing user.

    Returns the refreshed ``User`` instance.
    Raises ``ValueError`` if the user is not found.
    """
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**update_data)
        .returning(User)
    )
    result = await db.execute(stmt)
    await db.commit()

    updated_user = result.scalars().first()
    if updated_user is None:
        raise ValueError(f"User with id {user_id} not found.")

    await db.refresh(updated_user)
    return updated_user


async def user_exists(db: AsyncSession, email: str) -> bool:
    """Return ``True`` if a user with the given email already exists."""
    user = await get_user_by_email(db, email)
    return user is not None
