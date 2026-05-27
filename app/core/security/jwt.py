"""
JWT token creation and verification utilities.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenPayload(BaseModel):
    """Decoded JWT payload schema."""

    sub: str  # user ID
    exp: int  # expiration timestamp
    type: str  # "access" or "refresh"


def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a short-lived JWT access token.

    *data* must include a ``"sub"`` key with the user ID.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes,
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a long-lived JWT refresh token.

    *data* must include a ``"sub"`` key with the user ID.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days,
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Returns the full payload dict on success.
    Raises ``JWTError`` on invalid / expired tokens.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        sub: str | None = payload.get("sub")
        if sub is None:
            raise JWTError("Token payload missing 'sub' claim.")
        return payload
    except JWTError:
        raise
