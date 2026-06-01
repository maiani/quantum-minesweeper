# qminesweeper/stim_backend.py
from __future__ import annotations

import stim

from qminesweeper.quantum_backend import QuantumBackend, QuantumGate, StabilizerQuantumState

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


class StimState(StabilizerQuantumState):
    """Stim-based stabilizer simulation backend."""

    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    # ---------- internal helpers ----------

    def _init_state(self) -> None:
        """Initialize tableau to |0>^n."""
        self.tab = stim.TableauSimulator()
        self.tab.set_num_qubits(self.n)

    def _do1(self, opname: str, t: int) -> None:
        """Apply a single-qubit op by name to target index."""
        self.tab.do(stim.Circuit(f"{opname} {t}"))

    def _do2(self, opname: str, t0: int, t1: int) -> None:
        """Apply a two-qubit op by name to (t0, t1)."""
        self.tab.do(stim.Circuit(f"{opname} {t0} {t1}"))

    # ---------- public API ----------

    def reset(self) -> None:
        """Reset to |0>^n."""
        self._init_state()

    def expectation_pauli(self, idx: int, basis: str) -> float:
        """
        Return ⟨basis⟩ for qubit at idx.
        basis ∈ {"X","Y","Z"}.
        """
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Basis must be 'X','Y','Z'")
        pauli = ["I"] * self.n
        pauli[idx] = basis
        obs = stim.PauliString("".join(pauli))
        return float(self.tab.peek_observable_expectation(obs))

    def measure(self, idx: int, basis: str = "Z") -> int:
        """
        Projectively measure qubit `idx` in a Pauli basis (X, Y, or Z).
        We rotate into Z, measure, then rotate back, so the post-measurement
        state matches a true X/Y/Z measurement collapse.
        """
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
        two-qubit gates require exactly two targets. (See StabilizerQuantumState.)

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
            self._do2(_TWO_Q_STIM[gate_enum], targets[0], targets[1])
            return

        raise ValueError(f"Unsupported gate for Stim: {gate_enum}")


class StimBackend(QuantumBackend):
    """Factory that creates Stim stabilizer states."""

    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        return StimState(n_qubits)

    def random_clifford_circuit(self, n: int) -> list[tuple[str, list[int]]]:
        """
        Generate a random stabilizer circuit of size n using Stim.
        Returns a list of (gate, [qubit indices]) tuples compatible
        with QMineSweeperBoard.

        Uses the explicit "elimination" decomposition and **raises** on any op
        outside the known vocabulary, so an unmapped gate can never be silently
        dropped (which would yield a state that is not the sampled Clifford).
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
