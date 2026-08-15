import os
from project_qwe.config.settings import Settings


def test_database_url_from_settings() -> None:
    settings = Settings()
    assert settings.DATABASE_URL == "sqlite:///data/development.sqlite"


def test_database_url_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/test_custom.sqlite")
    custom_settings = Settings()
    assert custom_settings.DATABASE_URL == "sqlite:///data/test_custom.sqlite"
