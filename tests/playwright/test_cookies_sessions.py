"""Playwright API testing suite for HTTP Cookies and Session Management."""

from collections.abc import Generator
from pathlib import Path
import time
from urllib.parse import urlparse

from dotenv import dotenv_values, find_dotenv
from playwright.sync_api import APIRequestContext, Playwright
import pytest

from project_qwe.services.session_service import session_service

_env_test_path = find_dotenv(".env.test") or str(
    Path(__file__).resolve().parents[2] / ".env.test"
)
_test_env = dotenv_values(_env_test_path)

ADMIN_USERNAME = _test_env["TEST_ADMIN_USERNAME"]
ADMIN_PASSWORD = _test_env["TEST_ADMIN_PASSWORD"]
LEARNER_USERNAME = _test_env["TEST_LEARNER_USERNAME"]
LEARNER_PASSWORD = _test_env["TEST_LEARNER_PASSWORD"]
INVALID_USERNAME = _test_env["TEST_INVALID_USERNAME"]
INVALID_PASSWORD = _test_env["TEST_INVALID_PASSWORD"]


@pytest.fixture(autouse=True)
def clean_sessions() -> Generator[None, None, None]:
    """Ensure in-memory sessions are cleared before and after each test for strict isolation."""
    session_service.clear_all()
    yield
    session_service.clear_all()


def test_login_successful_sets_cookie(api_context: APIRequestContext) -> None:
    """Validate successful login sets an HTTP-only session cookie with correct attributes."""
    response = api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )

    assert response.status == 200
    assert response.ok is True

    payload = response.json()
    assert payload["message"] == "Login successful"
    assert payload["user"]["username"] == ADMIN_USERNAME
    assert payload["user"]["role"] == "admin"
    assert "password" not in payload["user"]
    assert "session_id" not in payload

    # Verify Set-Cookie header is returned by the server
    headers = response.headers
    set_cookie_raw = headers.get("set-cookie", "")
    assert "session_id=" in set_cookie_raw
    assert "httponly" in set_cookie_raw.lower()
    assert "path=/" in set_cookie_raw.lower()
    assert "samesite=lax" in set_cookie_raw.lower()

    # Verify Playwright parsed and stored the cookie in its context cookie jar
    cookies = api_context.cookies()
    session_cookie = next((c for c in cookies if c["name"] == "session_id"), None)
    assert session_cookie is not None
    assert session_cookie["httpOnly"] is True
    assert session_cookie["sameSite"] == "Lax"
    assert session_cookie["path"] == "/"
    assert len(session_cookie["value"]) > 0


def test_login_invalid_credentials(api_context: APIRequestContext) -> None:
    """Validate 401 Unauthorized for incorrect password without setting cookies."""
    response = api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": INVALID_PASSWORD},
    )

    assert response.status == 401
    assert "Invalid username or password" in response.json()["detail"]

    # Verify no session cookie was stored
    cookies = api_context.cookies()
    assert not any(c["name"] == "session_id" for c in cookies)


def test_login_missing_fields_validation_422(api_context: APIRequestContext) -> None:
    """Validate 422 Unprocessable Content when required fields are missing."""
    response = api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME},  # Missing password
    )
    assert response.status == 422


def test_get_current_user_with_session(api_context: APIRequestContext) -> None:
    """Validate reading the session_id cookie and returning user details."""
    # 1. Login to establish session
    login_res = api_context.post(
        "/session/login",
        data={"username": LEARNER_USERNAME, "password": LEARNER_PASSWORD},
    )
    assert login_res.status == 200

    # 2. Call /session/me (Playwright automatically attaches the session cookie)
    me_res = api_context.get("/session/me")
    assert me_res.status == 200
    user = me_res.json()
    assert user["username"] == LEARNER_USERNAME
    assert user["role"] == "learner"
    assert user["email"] == "david.learner@example.com"


def test_get_current_user_without_session_returns_401(
    api_context: APIRequestContext,
) -> None:
    """Validate 401 Unauthorized when /session/me is called without a session cookie."""
    response = api_context.get("/session/me")
    assert response.status == 401
    assert "not authenticated" in response.json()["detail"].lower()


def test_cookie_persistence_in_same_context(api_context: APIRequestContext) -> None:
    """Validate that APIRequestContext persists cookies across sequential requests."""
    # Step 1: Login
    api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )

    # Step 2: First protected request
    res1 = api_context.get("/session/me")
    assert res1.status == 200
    assert res1.json()["username"] == ADMIN_USERNAME

    # Step 3: Second protected request in the same context
    res2 = api_context.get("/session/status")
    assert res2.status == 200
    assert res2.json()["authenticated"] is True
    assert res2.json()["user"]["username"] == ADMIN_USERNAME


def test_context_isolation_separate_request_contexts(
    playwright: Playwright, base_url: str
) -> None:
    """Validate that two separate APIRequestContext instances do not share cookies."""
    # Context 1: Authenticated user
    context_1 = playwright.request.new_context(
        base_url=base_url, extra_http_headers={"Accept": "application/json"}
    )
    # Context 2: Anonymous user
    context_2 = playwright.request.new_context(
        base_url=base_url, extra_http_headers={"Accept": "application/json"}
    )

    try:
        # Login in context 1
        login_res = context_1.post(
            "/session/login",
            data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )
        assert login_res.status == 200
        assert len(context_1.cookies()) > 0

        # Context 2 should have no cookies and receive 401 on protected endpoint
        assert len(context_2.cookies()) == 0
        unauthorized_res = context_2.get("/session/me")
        assert unauthorized_res.status == 401
    finally:
        context_1.dispose()
        context_2.dispose()


def test_playwright_cookies_inspection(api_context: APIRequestContext) -> None:
    """Demonstrate context.cookies() inspection of all cookie metadata."""
    api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )

    all_cookies = api_context.cookies()
    assert len(all_cookies) == 1

    cookie = all_cookies[0]
    assert cookie["name"] == "session_id"
    assert isinstance(cookie["value"], str)
    assert cookie["httpOnly"] is True
    assert cookie["sameSite"] == "Lax"
    assert cookie["path"] == "/"
    assert cookie["expires"] > 0


def test_playwright_clear_cookies(api_context: APIRequestContext) -> None:
    """Demonstrate context.clear_cookies() purging all stored session cookies."""
    # Establish session
    api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert api_context.get("/session/me").status == 200

    # Purge cookies via Playwright API
    api_context.clear_cookies()
    assert len(api_context.cookies()) == 0

    # Request without cookie is rejected
    assert api_context.get("/session/me").status == 401


def test_playwright_add_cookies_manual_injection(
    api_context: APIRequestContext, base_url: str
) -> None:
    """Demonstrate context.add_cookies() manually injecting a valid server-side session."""
    # 1. Fetch demo user record
    from project_qwe.services.auth_demo_service import AuthDemoService

    auth_svc = AuthDemoService()
    user = auth_svc.authenticate_with_password(ADMIN_USERNAME, ADMIN_PASSWORD)
    assert user is not None

    # 2. Create session directly on server
    server_session = session_service.create_session(user)

    # 3. Manually add cookie to Playwright context using parsed domain
    parsed = urlparse(base_url)
    domain = parsed.hostname or "127.0.0.1"

    api_context.add_cookies(
        [
            {
                "name": "session_id",
                "value": server_session.session_id,
                "domain": domain,
                "path": "/",
                "httpOnly": True,
                "sameSite": "Lax",
            }
        ]
    )

    # 4. Call protected endpoint to verify injection succeeded
    response = api_context.get("/session/me")
    assert response.status == 200
    assert response.json()["username"] == ADMIN_USERNAME


def test_session_refresh_extends_expiration(api_context: APIRequestContext) -> None:
    """Validate POST /session/refresh extends the session and issues an updated cookie."""
    # Login with a short 10-second TTL
    login_res = api_context.post(
        "/session/login",
        data={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "ttl_seconds": 10,
        },
    )
    assert login_res.status == 200

    # Call refresh to extend session to default TTL
    refresh_res = api_context.post("/session/refresh")
    assert refresh_res.status == 200

    data = refresh_res.json()
    assert data["message"] == "Session refreshed successfully"
    assert data["user"]["username"] == ADMIN_USERNAME
    assert "expires_at" in data

    # Verify updated Set-Cookie header was sent
    assert "session_id=" in refresh_res.headers.get("set-cookie", "")

    # Protected endpoint remains accessible
    assert api_context.get("/session/me").status == 200


def test_session_refresh_without_session_returns_401(
    api_context: APIRequestContext,
) -> None:
    """Validate 401 Unauthorized when attempting to refresh without an active session."""
    response = api_context.post("/session/refresh")
    assert response.status == 401
    assert "cannot refresh" in response.json()["detail"].lower()


def test_logout_invalidates_session_and_clears_cookie(
    api_context: APIRequestContext,
) -> None:
    """Validate POST /session/logout clears cookie and invalidates session on server."""
    # 1. Login
    api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert api_context.get("/session/me").status == 200

    # Extract active session_id value before logout
    cookie_before = next(c for c in api_context.cookies() if c["name"] == "session_id")
    session_id_value = cookie_before["value"]

    # 2. Logout
    logout_res = api_context.post("/session/logout")
    assert logout_res.status == 200
    assert logout_res.json()["message"] == "Logged out successfully"

    # Verify Set-Cookie header contains deletion instructions (Max-Age=0 or past expires)
    set_cookie_raw = logout_res.headers.get("set-cookie", "")
    assert "session_id=" in set_cookie_raw
    assert "max-age=0" in set_cookie_raw.lower() or "expires=" in set_cookie_raw.lower()

    # 3. Subsequent /session/me should return 401
    assert api_context.get("/session/me").status == 401

    # 4. Verify server-side invalidation: even if client re-injects the old session_id, it is rejected
    api_context.clear_cookies()
    tampered_res = api_context.get(
        "/session/me",
        headers={"Cookie": f"session_id={session_id_value}"},
    )
    assert tampered_res.status == 401


def test_session_expiration_with_short_ttl(api_context: APIRequestContext) -> None:
    """Demonstrate expired session behavior using a controlled short TTL (1 second)."""
    # Login with a 1-second TTL
    login_res = api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD, "ttl_seconds": 1},
    )
    assert login_res.status == 200

    # Wait for session to expire without long sleep
    time.sleep(1.1)

    # Calling /session/me after expiration must return 401
    expired_res = api_context.get("/session/me")
    assert expired_res.status == 401
    assert "expired" in expired_res.json()["detail"].lower()


def test_server_side_forced_expiration(api_context: APIRequestContext) -> None:
    """Validate immediate session rejection via server-side expiration mechanism."""
    # Login
    api_context.post(
        "/session/login",
        data={"username": LEARNER_USERNAME, "password": LEARNER_PASSWORD},
    )
    assert api_context.get("/session/me").status == 200

    cookie = next(c for c in api_context.cookies() if c["name"] == "session_id")
    # Force server-side expiration
    assert session_service.expire_session(cookie["value"]) is True

    # Immediate rejection
    res = api_context.get("/session/me")
    assert res.status == 401


def test_session_status_unauthenticated(api_context: APIRequestContext) -> None:
    """Validate /session/status returns authenticated=False when no session exists."""
    response = api_context.get("/session/status")
    assert response.status == 200
    data = response.json()
    assert data["authenticated"] is False
    assert data["user"] is None
    assert data["expires_at"] is None


def test_session_status_authenticated(api_context: APIRequestContext) -> None:
    """Validate /session/status returns authenticated=True and user metadata when session exists."""
    api_context.post(
        "/session/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )

    response = api_context.get("/session/status")
    assert response.status == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == ADMIN_USERNAME
    assert data["expires_at"] is not None


def test_cookie_session_full_lifecycle_chaining(
    api_context: APIRequestContext,
) -> None:
    # 1. Initially unauthenticated
    initial_status = api_context.get("/session/status")
    assert initial_status.status == 200
    assert initial_status.json()["authenticated"] is False

    # 2. Login
    login = api_context.post(
        "/session/login",
        data={"username": LEARNER_USERNAME, "password": LEARNER_PASSWORD},
    )
    assert login.status == 200
    assert login.json()["user"]["username"] == LEARNER_USERNAME

    # 3. Status confirms authenticated
    status_auth = api_context.get("/session/status")
    assert status_auth.status == 200
    assert status_auth.json()["authenticated"] is True
    assert status_auth.json()["user"]["role"] == "learner"

    # 4. Fetch authenticated user profile
    profile = api_context.get("/session/me")
    assert profile.status == 200
    assert profile.json()["email"] == "david.learner@example.com"

    # 5. Refresh session
    refresh = api_context.post("/session/refresh")
    assert refresh.status == 200
    assert refresh.json()["message"] == "Session refreshed successfully"

    # 6. Logout
    logout = api_context.post("/session/logout")
    assert logout.status == 200
    assert logout.json()["message"] == "Logged out successfully"

    # 7. Status confirms unauthenticated
    final_status = api_context.get("/session/status")
    assert final_status.status == 200
    assert final_status.json()["authenticated"] is False

    # 8. Protected endpoint is rejected with 401
    protected = api_context.get("/session/me")
    assert protected.status == 401
