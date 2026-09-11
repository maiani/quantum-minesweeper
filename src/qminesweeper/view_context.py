"""One product configuration, projected into template and browser contracts.

The application owns configuration in :class:`qminesweeper.settings.Settings`.
Its ``product_config()`` method takes one validated snapshot and returns the
framework-free value object below. Jinja's historical uppercase keys and the
JavaScript renderer's lowercase keys are consumer adapters, not independent
sources of defaults.
"""

from __future__ import annotations

from dataclasses import dataclass

from qminesweeper.engine import PROBE_REGION_DEFAULT, PROBE_REGION_LIMIT
from qminesweeper.quantum_backend import ONE_QUBIT_GATES, TWO_QUBIT_GATES


def _gate_arities() -> dict[str, int]:
    """JSON-ready gate arities derived from the simulator contract."""
    return {
        **{gate.value.upper(): 1 for gate in ONE_QUBIT_GATES},
        **{gate.value.upper(): 2 for gate in TWO_QUBIT_GATES},
    }


@dataclass(frozen=True)
class ProductConfig:
    """Validated product choices shared by server pages and the browser app."""

    enable_help: bool
    enable_about: bool
    enable_tutorial: bool
    tutorial_url: str | None
    enable_survey: bool
    survey_url: str | None
    reset_policy: str
    enable_entanglement_probes: bool
    enable_browser_app: bool

    def template_features(self, *, browser_app_available: bool) -> dict:
        """Project into the legacy uppercase mapping consumed by Jinja."""
        return {
            "ENABLE_HELP": self.enable_help,
            "ENABLE_TUTORIAL": self.enable_tutorial,
            "TUTORIAL_URL": self.tutorial_url,
            "ENABLE_SURVEY": self.enable_survey,
            "SURVEY_URL": self.survey_url,
            "ENABLE_ABOUT": self.enable_about,
            "RESET_POLICY": self.reset_policy,
            "ENABLE_ENTANGLEMENT_PROBES": self.enable_entanglement_probes,
            "PROBE_REGION_LIMIT": PROBE_REGION_LIMIT,
            "PROBE_REGION_DEFAULT": PROBE_REGION_DEFAULT,
            "ENABLE_BROWSER_APP": self.enable_browser_app and browser_app_available,
        }

    def browser_product(self) -> dict:
        """Product choices needed by browser setup before a new game."""
        return {
            "entanglement_probes": self.enable_entanglement_probes,
            "probe_region_default": PROBE_REGION_DEFAULT,
        }

    def game_config(
        self,
        *,
        entanglement_probes: bool | None = None,
        two_area_probes: bool = False,
    ) -> dict:
        """Project into the lowercase contract consumed by ``render.js``."""
        probes = self.enable_entanglement_probes if entanglement_probes is None else entanglement_probes
        return {
            "reset_policy": self.reset_policy,
            "enable_survey": self.enable_survey,
            "survey_url": self.survey_url,
            "gate_arities": _gate_arities(),
            "entanglement_probes": probes,
            "two_area_probes": two_area_probes,
        }
