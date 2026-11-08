"""Business logic and credential validation for authentication demo.

Per architecture conventions, all domain verification logic lives in services,
keeping API route handlers thin. Credentials are validated using constant-time
comparisons (`secrets.compare_digest`) to prevent timing side-channel attacks.
"""

import secrets

from project_qwe.config.settings import settings
from project_qwe.schemas.auth_demo import UserProfile


def authenticate_bearer_token(token: str) -> UserProfile | None:
    """Validate a Bearer token against configured settings.

    Returns:
        UserProfile if the token matches, None otherwise.
    """
    if not token:
        return None

    if secrets.compare_digest(token, settings.AUTH_DEMO_BEARER_TOKEN):
        return UserProfile(
            username="bearer_user",
            email="bearer_user@example.com",
            auth_method="bearer",
            role="learner",
        )
    return None


def authenticate_api_key(api_key: str) -> UserProfile | None:
    """Validate an API key against configured settings.

    Returns:
        UserProfile if the API key matches, None otherwise.
    """
    if not api_key:
        return None

    if secrets.compare_digest(api_key, settings.AUTH_DEMO_API_KEY):
        return UserProfile(
            username="api_key_user",
            email="api_key_user@example.com",
            auth_method="api_key",
            role="developer",
        )
    return None


def authenticate_basic_credentials(
    username: str, password: str
) -> UserProfile | None:
    """Validate HTTP Basic credentials against configured settings.

    Returns:
        UserProfile if username and password match, None otherwise.
    """
    if not username or not password:
        return None

    username_matches = secrets.compare_digest(
        username, settings.AUTH_DEMO_BASIC_USERNAME
    )
    password_matches = secrets.compare_digest(
        password, settings.AUTH_DEMO_BASIC_PASSWORD
    )

    if username_matches and password_matches:
        return UserProfile(
            username=username,
            email=f"{username}@example.com",
            auth_method="basic",
            role="learner",
        )
    return None
