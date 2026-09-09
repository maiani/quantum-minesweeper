# qminesweeper/chppy_backend.py
"""Pyodide-friendly stabilizer backend, a thin adapter over the standalone
``chppy`` stabilizer tableau library (``chppy.CHP``).

``chppy`` is an independent, game-agnostic package that speaks plain gate-name
strings. This adapter is the single point of contact between it and the game:
it glues it to the ``StabilizerQuantumState`` / ``QuantumBackend`` contracts,
accepting ``QuantumGate`` enums (what ``engine.apply_command`` hands the board)
as well as bare strings, and supplying the random-circuit factory the board uses
to sample entangled mine layouts. All the tableau math lives in ``chppy``;
nothing here re-implements it, and no game concept leaks the other way.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from chppy import CHP
from qminesweeper.quantum_backend import (
    QuantumBackend,
    QuantumGate,
    StabilizerQuantumState,
)


class ChppyState(CHP, StabilizerQuantumState):
    """A ``chppy`` tableau exposed as a game ``StabilizerQuantumState``.

    Inherits the entire tableau (the ``x`` / ``z`` / ``r`` arrays, ``n``, and
    all gate / measurement / expectation math) from :class:`chppy.CHP`. The only
    thing it adds is enum tolerance on :meth:`apply_gate`: the game passes
    ``QuantumGate`` members, while ``chppy`` expects the matching name strings.
    """

    def apply_gate(self, gate: QuantumGate | str, targets: list[int]) -> None:
        # The board/engine pass QuantumGate enums; chppy keys gates by the string
        # name (QuantumGate.value, e.g. "Sdg", "SXdg"). Normalise to that string.
        name = gate.value if isinstance(gate, QuantumGate) else str(gate)
        super().apply_gate(name, targets)


class ChppyBackend(QuantumBackend):
    """Factory for pure-Python stabilizer states (Pyodide-friendly)."""

    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        return ChppyState(n_qubits)

    def random_clifford_circuit(self, n: int, *, seed: Optional[int] = None) -> list[tuple[str, list[int]]]:
        """A random Clifford as a local {H, S, CX} circuit.

        Not a uniform random Clifford, but a sufficiently-scrambling one. The
        caller rejection-samples for the properties it needs, so uniformity is
        not required here; see "Simulator backends" in docs/architecture.md.

        ``seed`` is honoured, and gives **in-backend** reproducibility only: the
        same ``seed`` and ``n`` always return the same circuit here, and nothing
        more is promised. See "Simulator backends" in docs/architecture.md for
        how the backends differ and what a seed does not cover.

        A seeded call draws from its own generator, so it neither consumes nor
        disturbs the global NumPy stream. With no seed the draws come from that
        global stream, which is why ``np.random.seed(...)`` reproduces chppy
        boards and how the golden export tests pin board state. The two paths
        agree: ``random_clifford_circuit(n, seed=s)`` returns what
        ``np.random.seed(s)`` followed by ``random_clifford_circuit(n)`` returns,
        because ``RandomState(s)`` and the seeded global stream are the same
        sequence.
        """
        if n <= 0:
            return []
        # The np.random module exposes randint/choice/random with the same names
        # and semantics as RandomState, so both paths share the code below. An
        # explicit seed gets an independent generator; otherwise draw globally.
        rng = np.random.RandomState(seed) if seed is not None else np.random
        out: list[tuple[str, list[int]]] = []
        if n == 1:
            for _ in range(rng.randint(1, 4)):
                out.append((str(rng.choice(["H", "S"])), [0]))
            return out
        for _ in range(6 * n):
            if rng.random() < 0.5:
                q = int(rng.randint(n))
                out.append((str(rng.choice(["H", "S"])), [q]))
            else:
                a, b = (int(v) for v in rng.choice(n, size=2, replace=False))
                out.append(("CX", [a, b]))
        return out
