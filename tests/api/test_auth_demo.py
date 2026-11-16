"""Unit tests for the authentication demo API using FastAPI TestClient."""

import base64

from fastapi.testclient import TestClient

from project_qwe.config.settings import settings


def test_bearer_profile_success(client: TestClient) -> None:
    response = client.get(
        "/auth-demo/bearer/profile",
        headers={"Authorization": f"Bearer {settings.AUTH_DEMO_BEARER_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["auth_method"] == "bearer"
    assert data["username"] == "bearer_user"


def test_bearer_profile_missing_token(client: TestClient) -> None:
    response = client.get("/auth-demo/bearer/profile")
    assert response.status_code == 401
    assert "Missing Authorization header" in response.json()["detail"]


def test_bearer_profile_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/auth-demo/bearer/profile",
        headers={"Authorization": "Bearer bad-token-here"},
    )
    assert response.status_code == 401
    assert "Invalid or expired Bearer token" in response.json()["detail"]


def test_api_key_profile_success(client: TestClient) -> None:
    response = client.get(
        "/auth-demo/api-key/profile",
        headers={"X-API-Key": settings.AUTH_DEMO_API_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["auth_method"] == "api_key"
    assert data["username"] == "api_key_user"


def test_api_key_profile_missing(client: TestClient) -> None:
    response = client.get("/auth-demo/api-key/profile")
    assert response.status_code == 401
    assert "Missing X-API-Key header" in response.json()["detail"]


def test_api_key_profile_invalid(client: TestClient) -> None:
    response = client.get(
        "/auth-demo/api-key/profile",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]


def test_basic_profile_success(client: TestClient) -> None:
    raw = f"{settings.AUTH_DEMO_BASIC_USERNAME}:{settings.AUTH_DEMO_BASIC_PASSWORD}"
    token = base64.b64encode(raw.encode()).decode()
    response = client.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["auth_method"] == "basic"
    assert data["username"] == settings.AUTH_DEMO_BASIC_USERNAME


def test_basic_profile_missing(client: TestClient) -> None:
    response = client.get("/auth-demo/basic/profile")
    assert response.status_code == 401
    assert "Missing HTTP Basic credentials" in response.json()["detail"]


def test_basic_profile_invalid_user(client: TestClient) -> None:
    raw = f"wronguser:{settings.AUTH_DEMO_BASIC_PASSWORD}"
    token = base64.b64encode(raw.encode()).decode()
    response = client.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {token}"},
    )
    assert response.status_code == 401
    assert "Invalid HTTP Basic credentials" in response.json()["detail"]


def test_basic_profile_invalid_password(client: TestClient) -> None:
    raw = f"{settings.AUTH_DEMO_BASIC_USERNAME}:wrongpassword"
    token = base64.b64encode(raw.encode()).decode()
    response = client.get(
        "/auth-demo/basic/profile",
        headers={"Authorization": f"Basic {token}"},
    )
    assert response.status_code == 401
    assert "Invalid HTTP Basic credentials" in response.json()["detail"]
