# qminesweeper/purepy_backend.py
"""Pyodide-friendly stabilizer backend, a thin adapter over the standalone CHP
tableau (``chp_tableau.CHP``).

The CHP module is game-agnostic and speaks plain gate-name strings. This adapter
glues it to the game's ``StabilizerQuantumState`` / ``QuantumBackend`` contracts:
it accepts ``QuantumGate`` enums (what ``engine.apply_command`` hands the board)
as well as bare strings, and supplies the random-circuit factory the board uses
to sample entangled mine layouts. All the tableau math lives in CHP; nothing
here re-implements it.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from qminesweeper.chp_tableau import CHP
from qminesweeper.quantum_backend import (
    QuantumBackend,
    QuantumGate,
    StabilizerQuantumState,
)


class PurePyState(CHP, StabilizerQuantumState):
    """A CHP tableau exposed as a game ``StabilizerQuantumState``.

    Inherits the entire tableau (the ``x`` / ``z`` / ``r`` arrays, ``n``, and
    all gate / measurement / expectation math) from :class:`CHP`. The only thing
    it adds is enum tolerance on :meth:`apply_gate`: the game passes
    ``QuantumGate`` members, while CHP expects the matching name strings.
    """

    def apply_gate(self, gate: QuantumGate | str, targets: list[int]) -> None:
        # The board/engine pass QuantumGate enums; CHP keys gates by the string
        # name (QuantumGate.value, e.g. "Sdg", "SXdg"). Normalise to that string.
        name = gate.value if isinstance(gate, QuantumGate) else str(gate)
        super().apply_gate(name, targets)


class PurePyBackend(QuantumBackend):
    """Factory for pure-Python stabilizer states (Pyodide-friendly)."""

    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        return PurePyState(n_qubits)

    def random_clifford_circuit(self, n: int, *, seed: Optional[int] = None) -> list[tuple[str, list[int]]]:
        """A random Clifford as a local {H, S, CX} circuit.

        Not a uniform random Clifford, but a sufficiently-scrambling circuit;
        QMineSweeperBoard.span_random_stabilizer_mines rejection-samples for the
        properties it needs. `seed` is accepted for interface parity.
        """
        if n <= 0:
            return []
        out: list[tuple[str, list[int]]] = []
        if n == 1:
            for _ in range(np.random.randint(1, 4)):
                out.append((str(np.random.choice(["H", "S"])), [0]))
            return out
        for _ in range(6 * n):
            if np.random.random() < 0.5:
                q = int(np.random.randint(n))
                out.append((str(np.random.choice(["H", "S"])), [q]))
            else:
                a, b = (int(v) for v in np.random.choice(n, size=2, replace=False))
                out.append(("CX", [a, b]))
        return out
