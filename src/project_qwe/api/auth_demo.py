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

from project_qwe.services.auth_demo_service import AuthDemoService

DemoUser = AuthDemoService.DemoUser
auth_demo_service = AuthDemoService()

router = APIRouter(prefix="/auth-demo", tags=["auth-demo"])

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
basic_scheme = HTTPBasic(auto_error=False)


def get_auth_service() -> AuthDemoService:
    """Dependency provider returning the active AuthDemoService instance."""
    return auth_demo_service


def get_current_bearer_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthDemoService, Depends(get_auth_service)],
) -> DemoUser:
    """Dependency to validate Bearer token and return the authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = service.authenticate_bearer_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_api_key_user(
    api_key: Annotated[str | None, Depends(api_key_header_scheme)],
    service: Annotated[AuthDemoService, Depends(get_auth_service)],
) -> DemoUser:
    """Dependency to validate API key from X-API-Key header and return user."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    user = service.authenticate_api_key(api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return user


def get_current_basic_user(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(basic_scheme)],
    service: Annotated[AuthDemoService, Depends(get_auth_service)],
) -> DemoUser:
    """Dependency to validate HTTP Basic authentication and return user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HTTP Basic credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    user = service.authenticate_basic_credentials(
        credentials.username, credentials.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HTTP Basic credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user


@router.get("/bearer/profile", response_model=DemoUser)
def get_bearer_profile(
    user: Annotated[DemoUser, Depends(get_current_bearer_user)],
) -> DemoUser:
    """Retrieve profile of the user authenticated via Bearer token."""
    return user


@router.get("/api-key/profile", response_model=DemoUser)
def get_api_key_profile(
    user: Annotated[DemoUser, Depends(get_current_api_key_user)],
) -> DemoUser:
    """Retrieve profile of the user authenticated via API key."""
    return user


@router.get("/basic/profile", response_model=DemoUser)
def get_basic_profile(
    user: Annotated[DemoUser, Depends(get_current_basic_user)],
) -> DemoUser:
    """Retrieve profile of the user authenticated via HTTP Basic auth."""
    return user
