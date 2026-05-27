"""
Pydantic schemas (DTOs) for authentication endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ------------------------------------------------------------------ #
# Request schemas
# ------------------------------------------------------------------ #

class UserRegister(BaseModel):
    """Payload for POST /auth/register."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenRefresh(BaseModel):
    """Payload for POST /auth/refresh."""

    refresh_token: str


# ------------------------------------------------------------------ #
# Response schemas
# ------------------------------------------------------------------ #

class UserResponse(BaseModel):
    """Public user representation returned by the API."""

    id: uuid.UUID
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT token pair returned after login/register/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
