# qminesweeper/stim_backend.py
from __future__ import annotations

import stim

from qminesweeper.quantum_backend import QuantumBackend, QuantumGate, StabilizerQuantumState


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

        # one-qubit gates
        if gate_enum == QuantumGate.X:
            for t in targets:
                self._do1("X", t)
                return
        if gate_enum == QuantumGate.Y:
            for t in targets:
                self._do1("Y", t)
                return
        if gate_enum == QuantumGate.Z:
            for t in targets:
                self._do1("Z", t)
                return
        if gate_enum == QuantumGate.H:
            for t in targets:
                self._do1("H", t)
                return
        if gate_enum == QuantumGate.S:
            for t in targets:
                self._do1("S", t)
                return
        if gate_enum == QuantumGate.Sdg:
            for t in targets:
                self._do1("S_DAG", t)
                return
        if gate_enum == QuantumGate.SX:
            for t in targets:
                self._do1("SQRT_X", t)
                return
        if gate_enum == QuantumGate.SXdg:
            for t in targets:
                self._do1("SQRT_X_DAG", t)
                return
        if gate_enum == QuantumGate.SY:
            for t in targets:
                self._do1("SQRT_Y", t)
                return
        if gate_enum == QuantumGate.SYdg:
            for t in targets:
                self._do1("SQRT_Y_DAG", t)
                return

        # two-qubit gates
        if gate_enum == QuantumGate.CX:
            if len(targets) != 2:
                raise ValueError("CX expects 2 targets")
            self._do2("CX", targets[0], targets[1])
            return
        if gate_enum == QuantumGate.CY:
            if len(targets) != 2:
                raise ValueError("CY expects 2 targets")
            self._do2("CY", targets[0], targets[1])
            return
        if gate_enum == QuantumGate.CZ:
            if len(targets) != 2:
                raise ValueError("CZ expects 2 targets")
            self._do2("CZ", targets[0], targets[1])
            return
        if gate_enum == QuantumGate.SWAP:
            if len(targets) != 2:
                raise ValueError("SWAP expects 2 targets")
            self._do2("SWAP", targets[0], targets[1])
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
        """
        tableau = stim.Tableau.random(n)
        circuit = tableau.to_circuit()

        ARITY = {
            "H": 1,
            "S": 1,
            "S_DAG": 1,
            "X": 1,
            "Y": 1,
            "Z": 1,
            "CX": 2,
            "CY": 2,
            "CZ": 2,
            "SWAP": 2,
        }
        name_map = {"S_DAG": "Sdg"}  # map Stim to your board conventions

        out: list[tuple[str, list[int]]] = []
        for inst in circuit:
            name = inst.name.upper()
            if name not in ARITY:
                continue

            name = name_map.get(name, name)
            arity = ARITY[name]  # 1 or 2

            qubits = [t.value for t in inst.targets_copy() if t.is_qubit_target]
            if len(qubits) % arity != 0:
                raise ValueError(f"Unexpected arity for {name}: {qubits}")

            for i in range(0, len(qubits), arity):
                out.append((name, qubits[i : i + arity]))

        return out
