"""Pydantic schemas for session authentication, user representation, and status checks."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Payload accepted by POST /session/login."""

    username: str = Field(..., min_length=1, description="Username of the user")
    password: str = Field(..., min_length=1, description="Raw password of the user")
    ttl_seconds: int | None = Field(
        None,
        gt=0,
        description="Optional custom session duration in seconds (useful for testing expiration)",
    )

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    """Safe public representation of an authenticated user."""

    id: int
    username: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class LoginResponse(BaseModel):
    """Response returned upon successful session login."""

    message: str = "Login successful"
    user: UserResponse

    model_config = ConfigDict(extra="forbid")


class SessionRefreshResponse(BaseModel):
    """Response returned when an active session is refreshed."""

    message: str = "Session refreshed successfully"
    user: UserResponse
    expires_at: datetime

    model_config = ConfigDict(extra="forbid")


class LogoutResponse(BaseModel):
    """Response returned upon session logout."""

    message: str = "Logged out successfully"

    model_config = ConfigDict(extra="forbid")


class SessionStatusResponse(BaseModel):
    """Response returned by GET /session/status indicating current session state."""

    authenticated: bool
    user: UserResponse | None = None
    expires_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")
