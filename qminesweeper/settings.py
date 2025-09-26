# qminesweeper/settings.py
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings for Quantum Minesweeper.
    """

    # --- Backend settings ---
    ABANDON_THRESHOLD_MIN: int = 30

    # --- Feature flags ---
    ENABLE_HELP: bool = True
    ENABLE_ABOUT: bool = True    
    ENABLE_TUTORIAL: bool = False
    ENABLE_SURVEY : bool = False

    # Reset policy: "never", "sandbox", "any"
    RESET_POLICY: str = "sandbox"

    # External links
    TUTORIAL_URL: str | None = None
    SURVEY_URL: str | None = None

    # --- Auth ---
    ENABLE_AUTH: bool = True
    USER: str | None = None
    PASS: str | None = None
    ADMIN_PASS: str | None = None

    # --- Runtime ---
    BACKEND: str = "stim"  # "stim" | "qiskit"
    BASE_URL: str = "http://127.0.0.1:8080"
    model_config = SettingsConfigDict(
        env_prefix="QMS_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
