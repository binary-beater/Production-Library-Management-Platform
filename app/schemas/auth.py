"""Pydantic schemas for authentication requests, responses, and validation."""

import re
import uuid
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.enums import UserRole


class PasswordPolicyMixin:
    """Helper mixin to validate password strength constraints."""

    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength rules (BR-003).

        Must have:
        - 8 to 128 characters.
        - At least 1 uppercase letter.
        - At least 1 lowercase letter.
        - At least 1 digit.
        - At least 1 special character (@$!%*?&).
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v) > 128:
            raise ValueError("Password must be no more than 128 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Password must contain at least one special character (@$!%*?&)")
        return v


class UserRegisterRequest(BaseModel, PasswordPolicyMixin):
    """Schema for validating new user registration payload."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        """Apply password validation policy check."""
        return cls.validate_password_strength(v)


class UserLoginRequest(BaseModel):
    """Schema for validating user login credentials payload."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class ClientMetadata(BaseModel):
    """Encapsulates client context metadata parameters parsed from request headers."""

    ip_address: str | None = None
    user_agent: str | None = None
    device_name: str | None = None


class TokenResponse(BaseModel):
    """Response returned upon successful authentication containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # Default access token duration: 15 minutes (900 seconds)


class TokenRefreshRequest(BaseModel):
    """Request payload to request access token rotation using a refresh token."""

    refresh_token: str = Field(..., min_length=1)


class UserMeResponse(BaseModel):
    """User profile details response schema representing /me endpoint response."""

    id: str
    name: str
    email: EmailStr
    role: UserRole
    status: str

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v: Any) -> str:
        """Coerce incoming UUID instances to string to prevent serialization errors."""
        if isinstance(v, uuid.UUID):
            return str(v)
        return str(v)

    class Config:
        from_attributes = True
