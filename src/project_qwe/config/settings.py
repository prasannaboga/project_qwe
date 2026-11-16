import os

from dotenv import find_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str:
    """Identify .env vs .env.test using python-dotenv find_dotenv based on ENV mode."""
    if "ENV_FILE" in os.environ:
        return os.environ["ENV_FILE"]
    env_mode = os.getenv("ENV", os.getenv("ENVIRONMENT", "development")).lower()
    target = ".env.test" if env_mode == "test" else ".env"
    return find_dotenv(target) or target


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///data/development.sqlite"
    MCP_TODOS_PROGRESS_DELAY_SECONDS: int = 0
    USERS_CSV_FILE: str = "data/demo_users_details.csv"

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
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
