# qminesweeper/settings.py
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Feature flags
    ENABLE_HELP: bool = True
    ENABLE_TUTORIAL: bool = True

    # Docs links (optional)
    TUTORIAL_URL: str | None = None

    # Auth
    ENABLE_AUTH: bool = True
    USER: str | None = None
    PASS: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="QMS_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
