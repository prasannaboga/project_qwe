import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str:
    """Resolve environment file based on ENV/ENVIRONMENT mode (test vs development)."""
    if "ENV_FILE" in os.environ:
        return os.environ["ENV_FILE"]
    env_mode = os.getenv("ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env_mode == "test" and Path(".env.test").exists():
        return ".env.test"
    return ".env"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///data/development.sqlite"
    MCP_TODOS_PROGRESS_DELAY_SECONDS: int = 0
    USERS_CSV_FILE: str = "data/demo_users_details.csv"

    # Test Credentials (loaded from .env.test in test environment)
    TEST_ADMIN_TOKEN: str = "0b651ead14f13cd36f196dd4118baf41f9553d4c3ee403e163c24d9c92c95d5e"
    TEST_ADMIN_API_KEY: str = "36ccd7c98ed6b3bf"
    TEST_ADMIN_USERNAME: str = "admin_alice"
    TEST_ADMIN_PASSWORD: str = "AliceAdmin!92#"

    TEST_LEARNER_TOKEN: str = "f88ec327da118efcb48728bcab015e11582676cdc56d364df1995a3012668c07"
    TEST_LEARNER_API_KEY: str = "f86ee4adb7499126"
    TEST_LEARNER_USERNAME: str = "learner_david"
    TEST_LEARNER_PASSWORD: str = "DavidLearn!61&"

    TEST_INVALID_TOKEN: str = "invalid-token-xyz-1234567890abcdef1234567890abcdef"
    TEST_INVALID_KEY: str = "invalid-key-9999"
    TEST_INVALID_USERNAME: str = "nonexistent_user"
    TEST_INVALID_PASSWORD: str = "WrongPassword!999"

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_mcp_todos_progress_delay(self) -> "Settings":
        """Allow only an off value or the documented progress-demo delay range."""
        delay = self.MCP_TODOS_PROGRESS_DELAY_SECONDS
        if delay != 0 and not 30 <= delay <= 45:
            raise ValueError(
                "MCP_TODOS_PROGRESS_DELAY_SECONDS must be 0 or between 30 and 45 seconds"
            )
        return self


settings = Settings()
