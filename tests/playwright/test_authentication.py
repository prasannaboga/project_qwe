"""Playwright API testing suite for Authentication Demo endpoints.

This module demonstrates API testing of multiple authentication mechanisms using
Playwright's APIRequestContext:
1. Bearer Token Authentication (Authorization: Bearer <token>)
2. API Key Authentication (Custom X-API-Key header)
3. HTTP Basic Authentication (Authorization: Basic <base64> and Playwright http_credentials)

Both request-level authentication and context-level pre-configured authentication
are demonstrated, along with positive and negative test cases.
"""

import base64

from playwright.sync_api import APIRequestContext, Playwright

from project_qwe.config.settings import settings

# Test credentials loaded from application configuration
VALID_BEARER_TOKEN = settings.AUTH_DEMO_BEARER_TOKEN
VALID_API_KEY = settings.AUTH_DEMO_API_KEY
VALID_BASIC_USER = settings.AUTH_DEMO_BASIC_USERNAME
VALID_BASIC_PASS = settings.AUTH_DEMO_BASIC_PASSWORD

INVALID_TOKEN = "invalid-token-xyz-12345"
INVALID_KEY = "invalid-api-key-99999"
INVALID_USER = "wronguser"
INVALID_PASS = "wrongpassword"


# ===========================================================================
# 1. Bearer Token Authentication Tests
# ===========================================================================

def test_bearer_auth_valid_token_request_level(api_context: APIRequestContext) -> None:
    """Demonstrate Bearer auth by passing the Authorization header per request."""
    response = api_context.get(
        "/auth-demo/bearer/profile",
        headers={"Authorization": f"Bearer {VALID_BEARER_TOKEN}"},
    )

    # Status and ok assertions
    assert response.status == 200
    assert response.ok is True

    # Body validation
    data = response.json()
    assert data["username"] == "bearer_user"
    assert data["email"] == "bearer_user@example.com"
    assert data["auth_method"] == "bearer"
    assert data["role"] == "learner"


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
    """Demonstrate Bearer auth configured globally at APIRequestContext creation.

    Useful when all requests executed by a test suite share the same Bearer token.
    """
    authenticated_context = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={
            "Authorization": f"Bearer {VALID_BEARER_TOKEN}",
            "Accept": "application/json",
        },
    )

    try:
        # Request does not need to specify headers; context injects them automatically
        response = authenticated_context.get("/auth-demo/bearer/profile")

        assert response.status == 200
        assert response.ok is True
        assert response.json()["auth_method"] == "bearer"
    finally:
        authenticated_context.dispose()


# ===========================================================================
# 2. API Key Authentication Tests
# ===========================================================================

def test_api_key_auth_valid_key_request_level(api_context: APIRequestContext) -> None:
    """Demonstrate API key authentication passed via custom X-API-Key request header."""
    response = api_context.get(
        "/auth-demo/api-key/profile",
        headers={"X-API-Key": VALID_API_KEY},
    )

    assert response.status == 200
    assert response.ok is True

    data = response.json()
    assert data["username"] == "api_key_user"
    assert data["email"] == "api_key_user@example.com"
    assert data["auth_method"] == "api_key"
    assert data["role"] == "developer"


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
            "X-API-Key": VALID_API_KEY,
            "Accept": "application/json",
        },
    )

    try:
        response = authenticated_context.get("/auth-demo/api-key/profile")
        assert response.status == 200
        assert response.ok is True
        assert response.json()["auth_method"] == "api_key"
    finally:
        authenticated_context.dispose()


# ===========================================================================
# 3. HTTP Basic Authentication Tests
# ===========================================================================

def test_basic_auth_valid_credentials_request_header(
    api_context: APIRequestContext,
) -> None:
    """Demonstrate Basic auth by formatting and sending 'Authorization: Basic <base64>'."""
    credentials_raw = f"{VALID_BASIC_USER}:{VALID_BASIC_PASS}"
    encoded = base64.b64encode(credentials_raw.encode("utf-8")).decode("utf-8")

    response = api_context.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {encoded}"},
    )

    assert response.status == 200
    assert response.ok is True

    data = response.json()
    assert data["username"] == VALID_BASIC_USER
    assert data["email"] == f"{VALID_BASIC_USER}@example.com"
    assert data["auth_method"] == "basic"
    assert data["role"] == "learner"


def test_basic_auth_valid_credentials_playwright_http_credentials(
    playwright: Playwright, base_url: str
) -> None:
    """Demonstrate Playwright's native `http_credentials` APIRequestContext option.

    Playwright automatically encodes and attaches HTTP Basic authentication headers
    for matching hosts when `http_credentials={'username': ..., 'password': ...}` is supplied.
    """
    authenticated_context = playwright.request.new_context(
        base_url=base_url,
        http_credentials={
            "username": VALID_BASIC_USER,
            "password": VALID_BASIC_PASS,
        },
    )

    try:
        response = authenticated_context.get("/auth-demo/basic/profile")

        assert response.status == 200
        assert response.ok is True
        assert response.json()["username"] == VALID_BASIC_USER
        assert response.json()["auth_method"] == "basic"
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
    credentials_raw = f"{INVALID_USER}:{VALID_BASIC_PASS}"
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
    credentials_raw = f"{VALID_BASIC_USER}:{INVALID_PASS}"
    encoded = base64.b64encode(credentials_raw.encode("utf-8")).decode("utf-8")

    response = api_context.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {encoded}"},
    )

    assert response.status == 401
    assert response.ok is False
    assert "Invalid HTTP Basic credentials" in response.json()["detail"]
