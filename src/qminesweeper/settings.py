# qminesweeper/settings.py
from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal, Mapping

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from qminesweeper.view_context import ProductConfig

BackendName = Literal["chppy", "stim", "qiskit"]
ResetPolicy = Literal["never", "sandbox", "any"]

# These are the settings the admin form owns and persists. Credentials, paths,
# backend selection, external URLs, and deployment limits remain environment
# configuration so the dashboard cannot mutate operational secrets or topology.
ADMIN_SETTING_NAMES = (
    "ENABLE_HELP",
    "ENABLE_ABOUT",
    "ENABLE_TUTORIAL",
    "ENABLE_SURVEY",
    "ENABLE_ENTANGLEMENT_PROBES",
    "ENABLE_BROWSER_APP",
    "RESET_POLICY",
)


class Settings(BaseSettings):
    """
    Application settings for Quantum Minesweeper.
    """

    # --- Backend settings ---
    ABANDON_THRESHOLD_MIN: int = Field(default=30, gt=0)

    # --- Feature flags ---
    ENABLE_HELP: bool = True
    ENABLE_ABOUT: bool = True
    ENABLE_TUTORIAL: bool = False
    ENABLE_SURVEY: bool = False

    # Whether the region entanglement probe exists in this deployment. How many
    # regions a game gets is a separate, per-game setup choice.
    ENABLE_ENTANGLEMENT_PROBES: bool = True

    # Reset policy: "never", "sandbox", "any"
    RESET_POLICY: ResetPolicy = "sandbox"

    # --- Browser analytics ---
    # Whether this server accepts game reports from browser-only sessions, which
    # otherwise record nothing because they run without a server. On by default
    # during the beta, so a deployment collects the same statistics whichever way
    # its players play. The endpoint is unauthenticated by necessity, so it
    # validates strictly and marks what it stores as client-asserted.
    ENABLE_BROWSER_ANALYTICS: bool = True
    # Comma-separated origins allowed to post reports, for when the static build
    # is hosted somewhere other than this server. Empty means same-origin only,
    # which is the case when the server hands out the app itself.
    ANALYTICS_ALLOWED_ORIGINS: str = ""
    # Where a browser build sends its reports. Relative by default, so a build
    # reports to whichever origin serves it and one bundle works on any host.
    # Set it to empty to build an app that reports nothing.
    BROWSER_ANALYTICS_URL: str | None = "/analytics"
    # Public-ingest safeguards. Limits are per process; Cloud Run is deliberately
    # configured for one instance unless the server-store boundary is redesigned.
    ANALYTICS_RATE_LIMIT_PER_MINUTE: int = Field(default=60, gt=0)
    ANALYTICS_GLOBAL_LIMIT_PER_MINUTE: int = Field(default=600, gt=0)
    ANALYTICS_MAX_BROWSER_ROWS: int = Field(default=50_000, gt=0)
    ANALYTICS_RETENTION_DAYS: int = Field(default=365, gt=0)

    # --- Installable app ---
    # Whether this deployment offers the installable browser app at /app/.
    # This does not change how the site itself plays: the server-rendered game
    # still runs on the server. It adds a second way to play that runs entirely
    # in the visitor's browser and can be installed and used offline.
    # Needs a bundle to serve, which the Docker image builds and points
    # BROWSER_DIST_DIR at; with no bundle the flag has nothing to enable.
    ENABLE_BROWSER_APP: bool = True
    # Directory holding a built browser bundle (the output of
    # scripts/build_browser.py). Normally set by the image rather than by hand.
    BROWSER_DIST_DIR: str | None = None

    # External links
    TUTORIAL_URL: str | None = None
    SURVEY_URL: str | None = None
    GA_MEASUREMENT_ID: str | None = None

    # --- Auth ---
    ENABLE_AUTH: bool = True
    USER: str | None = None
    PASS: str | None = None
    ADMIN_PASS: str | None = None

    # --- Runtime ---
    BACKEND: BackendName = "chppy"
    BASE_URL: str = "http://127.0.0.1:8080"
    model_config = SettingsConfigDict(
        env_prefix="QMS_",
        env_file=".env",
        extra="ignore",
        validate_assignment=True,
    )

    def admin_values(self) -> dict[str, Any]:
        """JSON-serializable settings controlled by the admin dashboard."""
        return {name: getattr(self, name) for name in ADMIN_SETTING_NAMES}

    def product_config(self) -> ProductConfig:
        """Take one validated snapshot of all user-visible product choices."""
        return ProductConfig(
            enable_help=self.ENABLE_HELP,
            enable_about=self.ENABLE_ABOUT,
            enable_tutorial=self.ENABLE_TUTORIAL,
            tutorial_url=self.TUTORIAL_URL,
            enable_survey=self.ENABLE_SURVEY,
            survey_url=self.SURVEY_URL,
            reset_policy=self.RESET_POLICY,
            enable_entanglement_probes=self.ENABLE_ENTANGLEMENT_PROBES,
            enable_browser_app=self.ENABLE_BROWSER_APP,
        )

    def apply_admin_values(self, values: Mapping[str, Any]) -> None:
        """Atomically apply validated persisted values, ignoring unknown keys."""
        selected = {name: values[name] for name in ADMIN_SETTING_NAMES if name in values}
        validated = type(self).model_validate({**self.model_dump(), **selected})
        for name in ADMIN_SETTING_NAMES:
            setattr(self, name, getattr(validated, name))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
