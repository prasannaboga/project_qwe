"""Shared fixtures for Playwright API testing."""

from collections.abc import Generator
import os
import socket
import threading
import time

from playwright.sync_api import APIRequestContext, Playwright
import pytest


def _is_server_ready(url: str) -> bool:
    """Check if the API server at `url` is ready and returning 200 on /health."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{url}/health", timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def base_url() -> str:
    """Resolve the base URL for Playwright API testing.

    Order of precedence:
    1. Environment variable API_BASE_URL (if provided and reachable).
    2. Default development server at http://127.0.0.1:8000 (if running).
    3. In-process background uvicorn server started on a free local port.
    """
    env_url = os.getenv("API_BASE_URL")
    if env_url and _is_server_ready(env_url):
        return env_url

    default_url = "http://127.0.0.1:8000"
    if _is_server_ready(default_url):
        return default_url

    import uvicorn
    from project_qwe.main import app

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    server_url = f"http://127.0.0.1:{free_port}"
    config = uvicorn.Config(app=app, host="127.0.0.1", port=free_port, log_level="error")
    server = uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        if _is_server_ready(server_url):
            return server_url
        time.sleep(0.1)

    return server_url


@pytest.fixture
def api_context(
    playwright: Playwright, base_url: str
) -> Generator[APIRequestContext, None, None]:
    """Provide a clean Playwright APIRequestContext fixture with automatic disposal."""
    context: APIRequestContext = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={"Accept": "application/json"},
    )
    try:
        yield context
    finally:
        context.dispose()
