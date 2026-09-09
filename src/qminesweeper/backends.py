"""Simulator backend selection helpers.

Optional simulator packages are imported only when selected. This keeps local
chppy/browser workflows free of Stim/Qiskit import requirements while allowing
server deployments to opt into Stim.
"""

from __future__ import annotations

from qminesweeper.quantum_backend import QuantumBackend

VALID_BACKENDS = ("chppy", "stim", "qiskit")


def normalize_backend(name: str | None, default: str = "chppy") -> str:
    """Return a validated backend name."""
    chosen = (name or default).strip().lower()
    if chosen not in VALID_BACKENDS:
        allowed = ", ".join(VALID_BACKENDS)
        raise ValueError(f"Unknown backend {name!r} (use {allowed})")
    return chosen


def make_backend(name: str | None, default: str = "chppy") -> QuantumBackend:
    """Construct the selected simulator backend."""
    chosen = normalize_backend(name, default=default)
    if chosen == "chppy":
        from qminesweeper.chppy_backend import ChppyBackend

        return ChppyBackend()
    if chosen == "stim":
        from qminesweeper.stim_backend import StimBackend

        return StimBackend()

    from qminesweeper.qiskit_backend import QiskitBackend

    return QiskitBackend()
