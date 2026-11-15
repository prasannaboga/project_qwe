from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
import threading

from project_qwe.services.auth_demo_service import DemoUser

DEFAULT_SESSION_TTL_SECONDS = 1800  # 30 minutes
SESSION_COOKIE_NAME = "session_id"


@dataclass
class SessionData:
    session_id: str
    user_id: int
    username: str
    email: str
    role: str
    created_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class SessionService:
    def __init__(self, default_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._default_ttl_seconds = default_ttl_seconds
        self._lock = threading.Lock()

    @property
    def default_ttl_seconds(self) -> int:
        return self._default_ttl_seconds

    def create_session(
        self, user: DemoUser, ttl_seconds: int | None = None
    ) -> SessionData:
        """Create and register a new session for an authenticated user."""
        ttl = ttl_seconds if (ttl_seconds is not None and ttl_seconds > 0) else self._default_ttl_seconds
        session_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)

        session = SessionData(
            session_id=session_id,
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=now,
            expires_at=expires_at,
        )

        with self._lock:
            self._sessions[session_id] = session

        return session

    def get_session(self, session_id: str | None) -> SessionData | None:
        """Retrieve an active session by ID. Expired sessions are evicted and return None."""
        if not session_id:
            return None

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if session.is_expired:
                del self._sessions[session_id]
                return None

            return session

    def refresh_session(
        self, session_id: str, extension_seconds: int | None = None
    ) -> SessionData | None:
        """Extend the lifetime of an active session."""
        ttl = (
            extension_seconds
            if (extension_seconds is not None and extension_seconds > 0)
            else self._default_ttl_seconds
        )
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.is_expired:
                if session is not None and session.is_expired:
                    del self._sessions[session_id]
                return None

            now = datetime.now(timezone.utc)
            session.expires_at = now + timedelta(seconds=ttl)
            return session

    def delete_session(self, session_id: str | None) -> bool:
        """Invalidate and remove a session from the store."""
        if not session_id:
            return False

        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def expire_session(self, session_id: str) -> bool:
        """Force a session to expire immediately (primarily for testing purposes)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            return True

    def clear_all(self) -> None:
        """Purge all sessions from memory."""
        with self._lock:
            self._sessions.clear()


session_service = SessionService()


def get_session_service() -> SessionService:
    """Dependency injection provider returning the singleton SessionService."""
    return session_service
