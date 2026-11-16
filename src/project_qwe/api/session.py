"""API routes for session-based authentication and cookie management."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from project_qwe.api.auth_demo import get_auth_service
from project_qwe.schemas.session import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionRefreshResponse,
    SessionStatusResponse,
    UserResponse,
)
from project_qwe.services.auth_demo_service import AuthDemoService
from project_qwe.services.session_service import (
    SESSION_COOKIE_NAME,
    SessionData,
    SessionService,
    get_session_service,
)

router = APIRouter(prefix="/session", tags=["session"])


def _set_session_cookie(
    response: Response,
    session: SessionData,
    ttl_seconds: int,
) -> None:
    """Helper to set consistent HTTP session cookie on response."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.session_id,
        max_age=ttl_seconds,
        expires=session.expires_at,
        path="/",
        httponly=True,
        # secure=False is used for local HTTP development and tests.
        # In production environments with TLS, this MUST be set to True.
        secure=False,
        samesite="lax",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with username and password to establish a session",
)
def login(
    payload: LoginRequest,
    response: Response,
    auth_service: Annotated[AuthDemoService, Depends(get_auth_service)],
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> LoginResponse:
    """Authenticate credentials, create a new session, and set the session_id HTTP cookie."""
    user = auth_service.authenticate_with_password(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    session = sessions.create_session(user, ttl_seconds=payload.ttl_seconds)
    ttl = (
        payload.ttl_seconds
        if (payload.ttl_seconds is not None and payload.ttl_seconds > 0)
        else sessions.default_ttl_seconds
    )
    _set_session_cookie(response, session, ttl)

    return LoginResponse(
        message="Login successful",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user details from session cookie",
)
def get_current_user(
    sessions: Annotated[SessionService, Depends(get_session_service)],
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> UserResponse:
    """Read session_id cookie and return authenticated user info. Returns 401 if missing or expired."""
    session = sessions.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: missing, invalid, or expired session cookie",
        )

    return UserResponse(
        id=session.user_id,
        username=session.username,
        email=session.email,
        role=session.role,
    )


@router.post(
    "/refresh",
    response_model=SessionRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Extend the current session lifetime",
)
def refresh_session(
    response: Response,
    sessions: Annotated[SessionService, Depends(get_session_service)],
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> SessionRefreshResponse:
    """Extend the session expiration and update the cookie max_age and expires headers."""
    session = sessions.refresh_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot refresh: missing, invalid, or expired session cookie",
        )

    _set_session_cookie(response, session, sessions.default_ttl_seconds)

    return SessionRefreshResponse(
        message="Session refreshed successfully",
        user=UserResponse(
            id=session.user_id,
            username=session.username,
            email=session.email,
            role=session.role,
        ),
        expires_at=session.expires_at,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout and invalidate the session",
)
def logout(
    response: Response,
    sessions: Annotated[SessionService, Depends(get_session_service)],
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> LogoutResponse:
    """Invalidate session in server storage and remove the session cookie from the client."""
    sessions.delete_session(session_id)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return LogoutResponse(message="Logged out successfully")


@router.get(
    "/status",
    response_model=SessionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check if the current request has an active valid session",
)
def get_session_status(
    sessions: Annotated[SessionService, Depends(get_session_service)],
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> SessionStatusResponse:
    """Return whether the current request is authenticated without raising 401 on missing cookies."""
    session = sessions.get_session(session_id)
    if session is None:
        return SessionStatusResponse(authenticated=False, user=None, expires_at=None)

    return SessionStatusResponse(
        authenticated=True,
        user=UserResponse(
            id=session.user_id,
            username=session.username,
            email=session.email,
            role=session.role,
        ),
        expires_at=session.expires_at,
    )
