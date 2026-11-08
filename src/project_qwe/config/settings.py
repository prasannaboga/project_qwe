from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    DATABASE_URL: str = "sqlite:///data/development.sqlite"
    MCP_TODOS_PROGRESS_DELAY_SECONDS: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
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
