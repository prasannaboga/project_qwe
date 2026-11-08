"""FastAPI endpoints demonstrating Bearer token, API key, and Basic authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import (
    APIKeyHeader,
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from project_qwe.schemas.auth_demo import UserProfile
from project_qwe.services import auth_demo as auth_service

router = APIRouter(prefix="/auth-demo", tags=["auth-demo"])

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
basic_scheme = HTTPBasic(auto_error=False)


def get_current_bearer_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserProfile:
    """Dependency to validate Bearer token and return the authenticated user profile."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile = auth_service.authenticate_bearer_token(credentials.credentials)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return profile


def get_current_api_key_user(
    api_key: Annotated[str | None, Depends(api_key_header_scheme)],
) -> UserProfile:
    """Dependency to validate API key from X-API-Key header and return user profile."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    profile = auth_service.authenticate_api_key(api_key)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return profile


def get_current_basic_user(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(basic_scheme)],
) -> UserProfile:
    """Dependency to validate HTTP Basic authentication and return user profile."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HTTP Basic credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    profile = auth_service.authenticate_basic_credentials(
        credentials.username, credentials.password
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HTTP Basic credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return profile


@router.get("/bearer/profile", response_model=UserProfile)
def get_bearer_profile(
    user: Annotated[UserProfile, Depends(get_current_bearer_user)],
) -> UserProfile:
    """Retrieve profile of the user authenticated via Bearer token."""
    return user


@router.get("/api-key/profile", response_model=UserProfile)
def get_api_key_profile(
    user: Annotated[UserProfile, Depends(get_current_api_key_user)],
) -> UserProfile:
    """Retrieve profile of the user authenticated via API key."""
    return user


@router.get("/basic/profile", response_model=UserProfile)
def get_basic_profile(
    user: Annotated[UserProfile, Depends(get_current_basic_user)],
) -> UserProfile:
    """Retrieve profile of the user authenticated via HTTP Basic auth."""
    return user
