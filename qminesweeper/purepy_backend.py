# qminesweeper/purepy_backend.py
from __future__ import annotations

from typing import Optional

import numpy as np

from qminesweeper.quantum_backend import (
    ONE_QUBIT_GATES,
    TWO_QUBIT_GATES,
    QuantumBackend,
    QuantumGate,
    StabilizerQuantumState,
)

# Pure-Python stabilizer simulator (Aaronson–Gottesman CHP tableau), numpy-vectorized.
# No C extensions, so it runs under Pyodide where Stim cannot. Matches the
# StabilizerQuantumState contract: single-qubit gates broadcast over targets,
# two-qubit gates require exactly two targets.


class PurePyState(StabilizerQuantumState):
    """CHP stabilizer tableau for n qubits.

    Rows 0..n-1 are destabilizers, n..2n-1 are stabilizers, row 2n is scratch.
    Columns 0..n-1 hold the X bits, a parallel array the Z bits, and `r` the
    phase bits (sign = (-1)^r).
    """

    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    # ---------- setup ----------
    def _init_state(self) -> None:
        n = self.n
        self.x = np.zeros((2 * n + 1, n), dtype=np.uint8)
        self.z = np.zeros((2 * n + 1, n), dtype=np.uint8)
        self.r = np.zeros(2 * n + 1, dtype=np.uint8)
        if n:
            np.fill_diagonal(self.x[0:n], 1)  # destabilizer i = X_i
            np.fill_diagonal(self.z[n : 2 * n], 1)  # stabilizer i = Z_i

    def reset(self) -> None:
        self._init_state()

    # ---------- single-qubit primitives (vectorized over generator rows) ----------
    # Applied to rows [0, 2n); the scratch row (2n) is managed only by measurement
    # and expectation, which reset it before use.
    @property
    def _M(self) -> int:
        return 2 * self.n

    def _H(self, a: int) -> None:
        m = self._M
        self.r[:m] ^= self.x[:m, a] & self.z[:m, a]
        col = self.x[:m, a].copy()
        self.x[:m, a] = self.z[:m, a]
        self.z[:m, a] = col

    def _S(self, a: int) -> None:
        m = self._M
        self.r[:m] ^= self.x[:m, a] & self.z[:m, a]
        self.z[:m, a] ^= self.x[:m, a]

    def _Sdg(self, a: int) -> None:
        self._S(a)
        self._S(a)
        self._S(a)  # S^3 = S†

    def _X(self, a: int) -> None:
        m = self._M
        self.r[:m] ^= self.z[:m, a]

    def _Z(self, a: int) -> None:
        m = self._M
        self.r[:m] ^= self.x[:m, a]

    def _Y(self, a: int) -> None:
        m = self._M
        self.r[:m] ^= self.x[:m, a] ^ self.z[:m, a]

    # ---------- two-qubit primitives ----------
    def _CX(self, a: int, b: int) -> None:
        m = self._M
        xa, za = self.x[:m, a], self.z[:m, a]
        xb, zb = self.x[:m, b], self.z[:m, b]
        self.r[:m] ^= xa & zb & (xb ^ za ^ 1)
        self.x[:m, b] ^= xa
        self.z[:m, a] ^= zb

    def _CZ(self, a: int, b: int) -> None:
        self._H(b)
        self._CX(a, b)
        self._H(b)

    def _CY(self, a: int, b: int) -> None:
        # control-Y = S_b · CX · S_b†
        self._Sdg(b)
        self._CX(a, b)
        self._S(b)

    def _SWAP(self, a: int, b: int) -> None:
        self._CX(a, b)
        self._CX(b, a)
        self._CX(a, b)

    # ---------- √ gates (decomposed; verified against Stim by the parity test) ----------
    def _SX(self, a: int) -> None:  # √X = H S H
        self._H(a)
        self._S(a)
        self._H(a)

    def _SXdg(self, a: int) -> None:  # √X† = H S† H
        self._H(a)
        self._Sdg(a)
        self._H(a)

    def _SY(self, a: int) -> None:  # √Y = S† · √X† · S
        self._S(a)
        self._SXdg(a)
        self._Sdg(a)

    def _SYdg(self, a: int) -> None:  # √Y† = S† · √X · S
        self._S(a)
        self._SX(a)
        self._Sdg(a)

    # ---------- public gate application ----------
    def apply_gate(self, gate: QuantumGate | str, targets: list[int]) -> None:
        if isinstance(gate, QuantumGate):
            g = gate
        else:
            try:
                g = QuantumGate[gate]
            except KeyError:
                raise ValueError(f"Unsupported gate for PurePy: {gate}")
        if g in ONE_QUBIT_GATES:
            for t in targets:
                self._apply_1q(g.value, int(t))
            return
        if g in TWO_QUBIT_GATES:
            if len(targets) != 2:
                raise ValueError(f"{g.value} expects 2 targets, got {len(targets)}")
            self._apply_2q(g.value, int(targets[0]), int(targets[1]))
            return
        raise ValueError(f"Unsupported gate for PurePy: {gate}")

    def _apply_1q(self, name: str, a: int) -> None:
        getattr(self, "_" + name)(a)

    def _apply_2q(self, name: str, a: int, b: int) -> None:
        getattr(self, "_" + name)(a, b)

    # ---------- rowsum (Pauli multiply row i into row h, tracking phase) ----------
    def _rowsum(self, h: int, i: int) -> None:
        xi = self.x[i].astype(np.int64)
        zi = self.z[i].astype(np.int64)
        xh = self.x[h].astype(np.int64)
        zh = self.z[h].astype(np.int64)

        g = np.zeros(self.n, dtype=np.int64)
        m11 = (xi == 1) & (zi == 1)
        m10 = (xi == 1) & (zi == 0)
        m01 = (xi == 0) & (zi == 1)
        g[m11] = zh[m11] - xh[m11]
        g[m10] = zh[m10] * (2 * xh[m10] - 1)
        g[m01] = xh[m01] * (1 - 2 * zh[m01])

        total = (2 * int(self.r[h]) + 2 * int(self.r[i]) + int(g.sum())) % 4
        self.r[h] = 1 if total == 2 else 0
        self.x[h] ^= self.x[i]
        self.z[h] ^= self.z[i]

    # ---------- Z-basis measurement (destructive) ----------
    def _measure_z(self, a: int) -> int:
        n, m = self.n, self._M
        stab_rows = np.nonzero(self.x[n:m, a])[0]
        if stab_rows.size > 0:
            p = n + int(stab_rows[0])
            for i in np.nonzero(self.x[:m, a])[0]:
                if int(i) != p:
                    self._rowsum(int(i), p)
            self.x[p - n] = self.x[p].copy()
            self.z[p - n] = self.z[p].copy()
            self.r[p - n] = self.r[p]
            self.x[p, :] = 0
            self.z[p, :] = 0
            self.z[p, a] = 1
            self.r[p] = int(np.random.randint(2))
            return int(self.r[p])
        # deterministic outcome via scratch row
        self.x[m, :] = 0
        self.z[m, :] = 0
        self.r[m] = 0
        for i in np.nonzero(self.x[:n, a])[0]:
            self._rowsum(m, n + int(i))
        return int(self.r[m])

    # ---------- expectation of a product of Z over a set of qubits (non-destructive) ----------
    def _expect_z_set(self, qubits: list[int]) -> float:
        n, m = self.n, self._M
        if not qubits:
            return 1.0
        cols = list(qubits)
        if np.any(self.x[n:m][:, cols].sum(axis=1) % 2):  # anticommutes with a stabilizer
            return 0.0
        self.x[m, :] = 0
        self.z[m, :] = 0
        self.r[m] = 0
        parity = self.x[:n][:, cols].sum(axis=1) % 2
        for i in np.nonzero(parity)[0]:
            self._rowsum(m, n + int(i))
        return -1.0 if self.r[m] else 1.0

    def pauli_expectation(self, paulis: dict[int, str]) -> float:
        """⟨P⟩ for a tensor Pauli given as {qubit: 'X'|'Y'|'Z'}. Non-destructive.

        Rotates each non-Z factor into Z, evaluates ⟨Z...Z⟩ (no Y-phase
        ambiguity), then undoes the rotations.
        """
        for q, p in paulis.items():
            if p == "X":
                self._H(q)
            elif p == "Y":
                self._Sdg(q)
                self._H(q)
        val = self._expect_z_set(list(paulis.keys()))
        for q, p in paulis.items():
            if p == "X":
                self._H(q)
            elif p == "Y":
                self._H(q)
                self._S(q)
        return val

    # ---------- StabilizerQuantumState API ----------
    def expectation_pauli(self, idx: int, basis: str) -> float:
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Basis must be 'X','Y','Z'")
        return self.pauli_expectation({idx: basis})

    def measure(self, idx: int, basis: str = "Z") -> int:
        if basis == "Z":
            return self._measure_z(idx)
        if basis == "X":
            self._H(idx)
            out = self._measure_z(idx)
            self._H(idx)
            return out
        if basis == "Y":
            self._Sdg(idx)
            self._H(idx)
            out = self._measure_z(idx)
            self._H(idx)
            self._S(idx)
            return out
        raise ValueError("Basis must be 'X','Y','Z'")


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
