# qminesweeper/view_context.py
"""Builders for the Jinja template context shared by the two runtimes.

Both the FastAPI server (`server.py`) and the static browser build
(`scripts/build_browser.py`) render the same templates and need the same context
*shape* — the feature-flag dict and the small app-config blob. Defining that
shape once, here, keeps the two runtimes from drifting: adding a flag is a
one-line change in one place instead of two that silently fall out of sync.

Framework-free on purpose (no FastAPI or settings imports) so the build script
can import it under the same constraints as engine.py. Callers pass the values
they have; the browser-build defaults live in the signatures.
"""

from __future__ import annotations

from qminesweeper.engine import PROBE_REGION_DEFAULT, PROBE_REGION_LIMIT
from qminesweeper.quantum_backend import ONE_QUBIT_GATES, TWO_QUBIT_GATES


def _gate_arities() -> dict[str, int]:
    """JSON-ready gate arities derived from the simulator contract."""
    return {
        **{gate.value.upper(): 1 for gate in ONE_QUBIT_GATES},
        **{gate.value.upper(): 2 for gate in TWO_QUBIT_GATES},
    }


def build_features(
    *,
    enable_help: bool = True,
    enable_tutorial: bool = False,
    tutorial_url: str | None = None,
    enable_survey: bool = False,
    survey_url: str | None = None,
    enable_about: bool = True,
    reset_policy: str = "any",
    enable_entanglement_probes: bool = True,
) -> dict:
    """The feature-flag dict templates read as ``FEATURES`` (header, setup, game).

    Defaults are the browser build's fixed product choices; the server overrides
    them from settings.
    """
    return {
        "ENABLE_HELP": enable_help,
        "ENABLE_TUTORIAL": enable_tutorial,
        "TUTORIAL_URL": tutorial_url,
        "ENABLE_SURVEY": enable_survey,
        "SURVEY_URL": survey_url,
        "ENABLE_ABOUT": enable_about,
        "RESET_POLICY": reset_policy,
        # Whether the deployment has the probe at all. The two constants beside
        # it are the game's own tiers, which the setup form renders as choices:
        # how many regions exist to offer, and which count setup starts from.
        "ENABLE_ENTANGLEMENT_PROBES": bool(enable_entanglement_probes),
        "PROBE_REGION_LIMIT": PROBE_REGION_LIMIT,
        "PROBE_REGION_DEFAULT": PROBE_REGION_DEFAULT,
    }


def build_config(
    *,
    reset_policy: str = "any",
    enable_survey: bool = False,
    survey_url: str | None = None,
    entanglement_probes: bool = True,
    two_area_probes: bool = False,
) -> dict:
    """The small app-config blob inlined into the game shell (``config``).

    Gate arity is semantic configuration, not presentation: JavaScript owns
    labels and layout but uses this derived mapping when constructing commands.
    """
    return {
        "reset_policy": reset_policy,
        "enable_survey": enable_survey,
        "survey_url": survey_url,
        "gate_arities": _gate_arities(),
        "entanglement_probes": entanglement_probes,
        "two_area_probes": two_area_probes,
    }
