"""Simulator backend selection helpers.

Optional simulator packages are imported only when selected. This keeps local
PurePy/browser workflows free of Stim/Qiskit import requirements while allowing
server deployments to opt into Stim.
"""

from __future__ import annotations

from qminesweeper.quantum_backend import QuantumBackend

VALID_BACKENDS = ("purepy", "stim", "qiskit")


def normalize_backend(name: str | None, default: str = "purepy") -> str:
    """Return a validated backend name."""
    chosen = (name or default).strip().lower()
    if chosen not in VALID_BACKENDS:
        allowed = ", ".join(VALID_BACKENDS)
        raise ValueError(f"Unknown backend {name!r} (use {allowed})")
    return chosen


def make_backend(name: str | None, default: str = "purepy") -> QuantumBackend:
    """Construct the selected simulator backend."""
    chosen = normalize_backend(name, default=default)
    if chosen == "purepy":
        from qminesweeper.purepy_backend import PurePyBackend

        return PurePyBackend()
    if chosen == "stim":
        from qminesweeper.stim_backend import StimBackend

        return StimBackend()

    from qminesweeper.qiskit_backend import QiskitBackend

    return QiskitBackend()
