"""Pydantic schemas for the authentication demo API."""

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """User profile returned upon successful authentication."""

    username: str = Field(..., description="Authenticated user handle")
    email: str = Field(..., description="Authenticated user email address")
    auth_method: str = Field(
        ..., description="Mechanism used to authenticate (bearer, api_key, basic)"
    )
    role: str = Field(default="learner", description="User role in the demo system")
