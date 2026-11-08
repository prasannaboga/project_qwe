"""Playwright API testing suite for Authentication Demo and Role-Based Access Control.

Demonstrates:
1. Bearer Token Authentication (Authorization: Bearer <token>)
2. API Key Authentication (Custom X-API-Key header)
3. HTTP Basic Authentication (Authorization: Basic <base64> and Playwright http_credentials)
4. Role-Based Access Control (403 Forbidden: Admin vs Learner)
5. Comprehensive Error Handling in Playwright (timeouts, error payloads, headers, assertions)

All test credentials and secrets are loaded from environment configuration (.env.test).
"""

import base64
from pathlib import Path

from dotenv import dotenv_values, find_dotenv
from playwright.sync_api import APIRequestContext, Error as PlaywrightError, Playwright
import pytest

# ---------------------------------------------------------------------------
# Credentials loaded directly from .env.test using python-dotenv
# ---------------------------------------------------------------------------

_env_test_path = find_dotenv(".env.test") or str(
    Path(__file__).resolve().parents[2] / ".env.test"
)
_test_env = dotenv_values(_env_test_path)

ADMIN_TOKEN = _test_env["TEST_ADMIN_TOKEN"]
ADMIN_API_KEY = _test_env["TEST_ADMIN_API_KEY"]
ADMIN_USERNAME = _test_env["TEST_ADMIN_USERNAME"]
ADMIN_PASSWORD = _test_env["TEST_ADMIN_PASSWORD"]

LEARNER_TOKEN = _test_env["TEST_LEARNER_TOKEN"]
LEARNER_API_KEY = _test_env["TEST_LEARNER_API_KEY"]
LEARNER_USERNAME = _test_env["TEST_LEARNER_USERNAME"]
LEARNER_PASSWORD = _test_env["TEST_LEARNER_PASSWORD"]

INVALID_TOKEN = _test_env["TEST_INVALID_TOKEN"]
INVALID_KEY = _test_env["TEST_INVALID_KEY"]
INVALID_USER = _test_env["TEST_INVALID_USERNAME"]
INVALID_PASS = _test_env["TEST_INVALID_PASSWORD"]


# ===========================================================================
# 1. Bearer Token Authentication Tests
# ===========================================================================

def test_bearer_auth_valid_token_request_level(api_context: APIRequestContext) -> None:
    """Demonstrate Bearer auth by passing the Authorization header per request."""
    response = api_context.get(
        "/auth-demo/bearer/profile",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )

    assert response.status == 200
    assert response.ok is True

    data = response.json()
    assert data["id"] == 1001
    assert data["username"] == ADMIN_USERNAME
    assert data["email"] == "alice.admin@example.com"
    assert data["role"] == "admin"


def test_bearer_auth_missing_token(api_context: APIRequestContext) -> None:
    """Demonstrate negative test when Bearer token header is omitted entirely."""
    response = api_context.get("/auth-demo/bearer/profile")

    assert response.status == 401
    assert response.ok is False
    assert "Missing Authorization header" in response.json()["detail"]
    assert "bearer" in response.headers.get("www-authenticate", "").lower()


def test_bearer_auth_invalid_token(api_context: APIRequestContext) -> None:
    """Demonstrate negative test when an invalid Bearer token is supplied."""
    response = api_context.get(
        "/auth-demo/bearer/profile",
        headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
    )

    assert response.status == 401
    assert response.ok is False
    assert "Invalid or expired Bearer token" in response.json()["detail"]


def test_bearer_auth_context_level_configuration(
    playwright: Playwright, base_url: str
) -> None:
    """Demonstrate Bearer auth configured globally at APIRequestContext creation."""
    authenticated_context = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={
            "Authorization": f"Bearer {LEARNER_TOKEN}",
            "Accept": "application/json",
        },
    )

    try:
        response = authenticated_context.get("/auth-demo/bearer/profile")

        assert response.status == 200
        assert response.ok is True
        data = response.json()
        assert data["username"] == LEARNER_USERNAME
        assert data["role"] == "learner"
    finally:
        authenticated_context.dispose()


# ===========================================================================
# 2. API Key Authentication Tests
# ===========================================================================

def test_api_key_auth_valid_key_request_level(api_context: APIRequestContext) -> None:
    """Demonstrate API key authentication passed via custom X-API-Key request header."""
    response = api_context.get(
        "/auth-demo/api-key/profile",
        headers={"X-API-Key": ADMIN_API_KEY},
    )

    assert response.status == 200
    assert response.ok is True

    data = response.json()
    assert data["id"] == 1001
    assert data["username"] == ADMIN_USERNAME
    assert data["role"] == "admin"


def test_api_key_auth_missing_header(api_context: APIRequestContext) -> None:
    """Demonstrate negative test when X-API-Key header is omitted."""
    response = api_context.get("/auth-demo/api-key/profile")

    assert response.status == 401
    assert response.ok is False
    assert "Missing X-API-Key header" in response.json()["detail"]


def test_api_key_auth_invalid_key(api_context: APIRequestContext) -> None:
    """Demonstrate negative test when an incorrect API key is provided."""
    response = api_context.get(
        "/auth-demo/api-key/profile",
        headers={"X-API-Key": INVALID_KEY},
    )

    assert response.status == 401
    assert response.ok is False
    assert "Invalid API Key" in response.json()["detail"]


def test_api_key_auth_context_level_configuration(
    playwright: Playwright, base_url: str
) -> None:
    """Demonstrate API key configured at APIRequestContext creation via extra_http_headers."""
    authenticated_context = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={
            "X-API-Key": LEARNER_API_KEY,
            "Accept": "application/json",
        },
    )

    try:
        response = authenticated_context.get("/auth-demo/api-key/profile")
        assert response.status == 200
        assert response.ok is True
        assert response.json()["username"] == LEARNER_USERNAME
    finally:
        authenticated_context.dispose()


# ===========================================================================
# 3. HTTP Basic Authentication Tests
# ===========================================================================

def test_basic_auth_valid_credentials_request_header(
    api_context: APIRequestContext,
) -> None:
    """Demonstrate Basic auth by formatting and sending 'Authorization: Basic <base64>'."""
    credentials_raw = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}"
    encoded = base64.b64encode(credentials_raw.encode("utf-8")).decode("utf-8")

    response = api_context.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {encoded}"},
    )

    assert response.status == 200
    assert response.ok is True

    data = response.json()
    assert data["username"] == ADMIN_USERNAME
    assert data["role"] == "admin"


def test_basic_auth_valid_credentials_playwright_http_credentials(
    playwright: Playwright, base_url: str
) -> None:
    """Demonstrate Playwright's native `http_credentials` APIRequestContext option."""
    authenticated_context = playwright.request.new_context(
        base_url=base_url,
        http_credentials={
            "username": LEARNER_USERNAME,
            "password": LEARNER_PASSWORD,
        },
    )

    try:
        response = authenticated_context.get("/auth-demo/basic/profile")

        assert response.status == 200
        assert response.ok is True
        assert response.json()["username"] == LEARNER_USERNAME
        assert response.json()["role"] == "learner"
    finally:
        authenticated_context.dispose()


def test_basic_auth_missing_credentials(api_context: APIRequestContext) -> None:
    """Demonstrate negative test when Basic authentication credentials are not provided."""
    response = api_context.get("/auth-demo/basic/profile")

    assert response.status == 401
    assert response.ok is False
    assert "Missing HTTP Basic credentials" in response.json()["detail"]
    assert "basic" in response.headers.get("www-authenticate", "").lower()


def test_basic_auth_invalid_username(api_context: APIRequestContext) -> None:
    """Demonstrate negative test when the username is incorrect."""
    credentials_raw = f"{INVALID_USER}:{ADMIN_PASSWORD}"
    encoded = base64.b64encode(credentials_raw.encode("utf-8")).decode("utf-8")

    response = api_context.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {encoded}"},
    )

    assert response.status == 401
    assert response.ok is False
    assert "Invalid HTTP Basic credentials" in response.json()["detail"]


def test_basic_auth_invalid_password(api_context: APIRequestContext) -> None:
    """Demonstrate negative test when the password is incorrect."""
    credentials_raw = f"{ADMIN_USERNAME}:{INVALID_PASS}"
    encoded = base64.b64encode(credentials_raw.encode("utf-8")).decode("utf-8")

    response = api_context.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {encoded}"},
    )

    assert response.status == 401
    assert response.ok is False
    assert "Invalid HTTP Basic credentials" in response.json()["detail"]


# ===========================================================================
# 4. Role-Based Access Control (403 Forbidden: Admin vs Learner)
# ===========================================================================

def test_admin_can_access_admin_dashboard(api_context: APIRequestContext) -> None:
    """Demonstrate that users with the 'admin' role are granted access (200 OK)."""
    response = api_context.get(
        "/auth-demo/admin/dashboard",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )

    assert response.status == 200
    assert response.ok is True

    data = response.json()
    assert data["role"] == "admin"
    assert data["access"] == "granted"
    assert ADMIN_USERNAME in data["message"]


def test_learner_forbidden_from_admin_dashboard(
    api_context: APIRequestContext,
) -> None:
    """Demonstrate that authenticated users without the 'admin' role receive 403 Forbidden.

    Highlights the critical difference between:
    - 401 Unauthorized: Authentication failure (unauthenticated)
    - 403 Forbidden: Authorization failure (authenticated, but lacking required permissions)
    """
    response = api_context.get(
        "/auth-demo/admin/dashboard",
        headers={"Authorization": f"Bearer {LEARNER_TOKEN}"},
    )

    # 403 Forbidden status validation
    assert response.status == 403
    assert response.ok is False

    # Detailed error message validation
    detail = response.json()["detail"]
    assert "Access forbidden" in detail
    assert "requires 'admin' role" in detail
    assert f"user '{LEARNER_USERNAME}' has role 'learner'" in detail


def test_unauthenticated_request_to_admin_dashboard_returns_401(
    api_context: APIRequestContext,
) -> None:
    """Demonstrate that unauthenticated requests to protected endpoints return 401, not 403."""
    response = api_context.get("/auth-demo/admin/dashboard")

    # Must be 401 Unauthorized because credentials were not supplied at all
    assert response.status == 401
    assert response.ok is False
    assert "Missing Authorization header" in response.json()["detail"]


# ===========================================================================
# 5. Playwright Error Handling Examples
# ===========================================================================

def test_error_handling_graceful_status_and_body_inspection(
    api_context: APIRequestContext,
) -> None:
    """Demonstrate robust error inspection patterns with Playwright APIResponse.

    Shows how to:
    1. Guard against assuming responses are always 2xx via `response.ok`.
    2. Safely inspect error payloads with fallback.
    3. Assert structured error fields like `detail`.
    """
    response = api_context.get(
        "/auth-demo/admin/dashboard",
        headers={"Authorization": f"Bearer {LEARNER_TOKEN}"},
    )

    # 1. Verify expected failure
    if not response.ok:
        assert response.status == 403
        try:
            payload = response.json()
            assert "detail" in payload
            assert isinstance(payload["detail"], str)
        except Exception as exc:
            pytest.fail(f"Expected JSON error response, but failed to parse: {exc}")
    else:
        pytest.fail("Expected 403 Forbidden, but received 2xx OK")


def test_error_handling_inspect_www_authenticate_header(
    api_context: APIRequestContext,
) -> None:
    """Demonstrate error inspection for HTTP challenge headers (RFC 7235).

    When returning 401 Unauthorized, servers must include a `WWW-Authenticate` header.
    Playwright makes it easy to inspect both dictionary and array representations of headers.
    """
    response = api_context.get("/auth-demo/bearer/profile")

    assert response.status == 401

    # Dictionary lookup (case-insensitive in Playwright)
    www_auth_header = response.headers.get("www-authenticate")
    assert www_auth_header is not None
    assert "bearer" in www_auth_header.lower()

    # Array representation inspection
    headers_list = response.headers_array
    auth_headers = [h for h in headers_list if h["name"].lower() == "www-authenticate"]
    assert len(auth_headers) >= 1
    assert "bearer" in auth_headers[0]["value"].lower()


def test_error_handling_playwright_request_timeout(playwright: Playwright) -> None:
    """Demonstrate handling Playwright request timeouts with `pytest.raises`.

    When an endpoint hangs or exceeds the configured timeout threshold,
    Playwright aborts the network request and raises `playwright.sync_api.Error`.
    """
    timeout_context = playwright.request.new_context(
        timeout=100,  # 100 milliseconds
    )

    try:
        # Requesting a non-routable address (TEST-NET) with a short timeout guarantees a timeout error
        with pytest.raises(PlaywrightError) as exc_info:
            timeout_context.get("http://10.255.255.1:81")

        assert "Timeout" in str(exc_info.value) or "timed out" in str(exc_info.value)
    finally:
        timeout_context.dispose()


def test_error_handling_unsupported_method_returns_405(
    api_context: APIRequestContext,
) -> None:
    """Demonstrate error handling for 405 Method Not Allowed.

    Sending an unsupported HTTP method (e.g., POST to a GET-only endpoint)
    allows tests to assert on standard HTTP status responses.
    """
    response = api_context.post("/auth-demo/admin/dashboard", data={})

    assert response.status == 405
    assert response.ok is False
    assert "Method Not Allowed" in response.status_text or response.status == 405
