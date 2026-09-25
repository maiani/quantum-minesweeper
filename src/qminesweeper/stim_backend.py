# qminesweeper/stim_backend.py
from __future__ import annotations

import numpy as np
import stim

from qminesweeper.quantum_backend import QuantumBackend, QuantumGate, StabilizerQuantumState, validate_subset

# QuantumGate -> Stim op name, split by arity.
_ONE_Q_STIM: dict[QuantumGate, str] = {
    QuantumGate.X: "X",
    QuantumGate.Y: "Y",
    QuantumGate.Z: "Z",
    QuantumGate.H: "H",
    QuantumGate.S: "S",
    QuantumGate.Sdg: "S_DAG",
    QuantumGate.SX: "SQRT_X",
    QuantumGate.SXdg: "SQRT_X_DAG",
    QuantumGate.SY: "SQRT_Y",
    QuantumGate.SYdg: "SQRT_Y_DAG",
}
_TWO_Q_STIM: dict[QuantumGate, str] = {
    QuantumGate.CX: "CX",
    QuantumGate.CY: "CY",
    QuantumGate.CZ: "CZ",
    QuantumGate.SWAP: "SWAP",
}

# Stim op name (as emitted by Tableau.to_circuit) -> (board gate name, arity).
_STIM_TO_BOARD: dict[str, tuple[str, int]] = {
    "H": ("H", 1),
    "S": ("S", 1),
    "S_DAG": ("Sdg", 1),
    "X": ("X", 1),
    "Y": ("Y", 1),
    "Z": ("Z", 1),
    "SQRT_X": ("SX", 1),
    "SQRT_X_DAG": ("SXdg", 1),
    "SQRT_Y": ("SY", 1),
    "SQRT_Y_DAG": ("SYdg", 1),
    "CX": ("CX", 2),
    "CY": ("CY", 2),
    "CZ": ("CZ", 2),
    "SWAP": ("SWAP", 2),
}


def _bit_rank(rows: list[int]) -> int:
    """Rank binary row bitmasks with integer Gaussian elimination."""
    basis: dict[int, int] = {}
    rank = 0
    for value in rows:
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                rank += 1
                break
    return rank


def _gf2_rank(matrix: np.ndarray) -> int:
    """GF(2) rank of a 0/1 matrix, one row per generator.

    Rows become integer bitmasks for ``_bit_rank``. Duplicate and zero rows
    cannot change the rank, so they are dropped first; a pair query projects
    every generator onto four columns, leaving at most fifteen distinct rows.
    """
    width = matrix.shape[1]
    if width <= 63:
        # Distinct powers of two, so the sum of a row's weights is its bitmask.
        weights = np.left_shift(np.uint64(1), np.arange(width, dtype=np.uint64))
        values = (matrix.astype(np.uint64) * weights).sum(axis=1, dtype=np.uint64)
        rows = np.unique(values[values != 0]).tolist()
    else:
        packed = np.packbits(matrix, axis=1)
        rows = list({int.from_bytes(row.tobytes(), "big") for row in packed if row.any()})
    return _bit_rank(rows)


class StimState(StabilizerQuantumState):
    """Stim-based stabilizer simulation backend."""

    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    # ---------- internal helpers ----------

    def _init_state(self) -> None:
        """Initialize tableau to |0⟩^n."""
        self.tab = stim.TableauSimulator()
        self.tab.set_num_qubits(self.n)
        self._stabilizer_bits: tuple[np.ndarray, np.ndarray] | None = None

    def _do1(self, opname: str, t: int) -> None:
        """Apply a single-qubit op by name to target index."""
        self._stabilizer_bits = None
        self.tab.do(stim.Circuit(f"{opname} {t}"))

    def _do2(self, opname: str, t0: int, t1: int) -> None:
        """Apply a two-qubit op by name to (t0, t1)."""
        self._stabilizer_bits = None
        self.tab.do(stim.Circuit(f"{opname} {t0} {t1}"))

    def _stabilizers(self) -> tuple[np.ndarray, np.ndarray]:
        """X and Z bits of a stabilizer generating set, one row per generator.

        Cached until the next gate, measurement or reset. A Sandbox reveal asks
        for thousands of region entropies of one unchanged state, and rebuilding
        and re-parsing the generators for every query took seconds on the
        largest boards, all of it on the server's event loop.
        """
        if self._stabilizer_bits is None:
            xs = np.zeros((self.n, self.n), dtype=np.uint8)
            zs = np.zeros((self.n, self.n), dtype=np.uint8)
            for row, stabilizer in enumerate(self.tab.canonical_stabilizers()):
                x, z = stabilizer.to_numpy()
                xs[row] = x[: self.n]
                zs[row] = z[: self.n]
            self._stabilizer_bits = (xs, zs)
        return self._stabilizer_bits

    # ---------- public API ----------

    def reset(self) -> None:
        """Reset to |0⟩^n."""
        self._init_state()

    def entanglement_entropy(self, subset: list[int]) -> float:
        """Return the stabilizer entropy of a region, in bits.

        Stim exposes canonical stabilizer generators as Pauli strings.  We
        project onto the smaller side R and use S(R) = rank(projection) - |R|,
        avoiding a state-vector conversion.
        """
        region = validate_subset(subset, self.n)
        k = len(region)
        if not region or k == self.n:
            return 0.0
        if k > self.n - k:
            region = tuple(q for q in range(self.n) if q not in region)
            k = len(region)
        xs, zs = self._stabilizers()
        cols = list(region)
        return float(_gf2_rank(np.concatenate((xs[:, cols], zs[:, cols]), axis=1)) - k)

    def expectation_pauli(self, idx: int, basis: str) -> float:
        """
        Return ⟨basis⟩ for qubit at idx.
        basis ∈ {"X","Y","Z"}.
        """
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Basis must be 'X','Y','Z'")
        # Checked here because Stim would silently grow the simulator to fit an
        # index past the end.
        if not 0 <= idx < self.n:
            raise IndexError(f"qubit {idx} out of range for {self.n} qubits")
        # peek_x/y/z return +1, -1 or 0 for one qubit directly. The general
        # peek_observable_expectation needs an n-qubit Pauli string built per
        # call, which made every whole-board observable quadratic in n.
        if basis == "X":
            return float(self.tab.peek_x(idx))
        if basis == "Y":
            return float(self.tab.peek_y(idx))
        return float(self.tab.peek_z(idx))

    def measure(self, idx: int, basis: str = "Z") -> int:
        """
        Projectively measure qubit `idx` in a Pauli basis (X, Y, or Z).
        We rotate into Z, measure, then rotate back, so the post-measurement
        state matches a true X/Y/Z measurement collapse.
        """
        self._stabilizer_bits = None
        if basis == "Z":
            return int(self.tab.measure(idx))

        if basis == "X":
            # U = H; U Z U† = X
            self._do1("H", idx)
            out = int(self.tab.measure(idx))
            self._do1("H", idx)
            return out

        if basis == "Y":
            # U = S_DAG ∘ H; U Z U† = Y
            self._do1("S_DAG", idx)
            self._do1("H", idx)
            out = int(self.tab.measure(idx))
            self._do1("H", idx)
            self._do1("S", idx)
            return out

        raise ValueError("Basis must be 'X','Y','Z'")

    def apply_gate(self, gate: QuantumGate | str, targets: list[int]) -> None:
        """
        Apply a supported Clifford gate.

        Single-qubit gates are broadcast over every index in ``targets``;
        two-qubit gates require exactly two distinct targets. (See
        StabilizerQuantumState.)

        Parameters
        ----------
        gate : QuantumGate | str
            Gate name or QuantumGate enum.
        targets : list[int]
            Target indices.
        """
        if isinstance(gate, str):
            try:
                gate_enum = QuantumGate[gate]
            except KeyError:
                raise ValueError(f"Unsupported gate for Stim: {gate}")
        else:
            gate_enum = gate

        if gate_enum in _ONE_Q_STIM:
            op = _ONE_Q_STIM[gate_enum]
            for t in targets:
                self._do1(op, t)
            return

        if gate_enum in _TWO_Q_STIM:
            if len(targets) != 2:
                raise ValueError(f"{gate_enum.value} expects 2 targets, got {len(targets)}")
            if targets[0] == targets[1]:
                raise ValueError(f"{gate_enum.value} needs two different qubits, got {targets[0]} twice")
            self._do2(_TWO_Q_STIM[gate_enum], targets[0], targets[1])
            return

        raise ValueError(f"Unsupported gate for Stim: {gate_enum}")


class StimBackend(QuantumBackend):
    """Factory that creates Stim stabilizer states."""

    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        return StimState(n_qubits)

    def random_clifford_circuit(self, n: int, *, seed: int | None = None) -> list[tuple[str, list[int]]]:
        """
        Generate a random stabilizer circuit of size n using Stim.
        Returns a list of (gate, [qubit indices]) tuples compatible
        with QMineSweeperBoard.

        Uses the explicit "elimination" decomposition and **raises** on any op
        outside the known vocabulary, so an unmapped gate can never be silently
        dropped (which would yield a state that is not the sampled Clifford).

        ``seed`` is accepted for QuantumBackend conformance and **ignored**:
        ``stim.Tableau.random`` exposes no seeding parameter, as of Stim 1.16.0
        and the 1.17 dev API. See "Simulator backends" in docs/architecture.md
        for why this backend must not swap in a seedable sampler instead, and
        the deferred-features section for the upstream status.
        """
        tableau = stim.Tableau.random(n)
        circuit = tableau.to_circuit(method="elimination")

        out: list[tuple[str, list[int]]] = []
        for inst in circuit:
            name = inst.name.upper()
            if name not in _STIM_TO_BOARD:
                raise ValueError(
                    f"Stim emitted unsupported gate {name!r} in random Clifford decomposition; extend _STIM_TO_BOARD."
                )
            board_name, arity = _STIM_TO_BOARD[name]

            qubits = [t.value for t in inst.targets_copy() if t.is_qubit_target]
            if len(qubits) % arity != 0:
                raise ValueError(f"Unexpected target count for {name}: {qubits}")

            for i in range(0, len(qubits), arity):
                out.append((board_name, qubits[i : i + arity]))

        return out
