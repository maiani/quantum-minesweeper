# qminesweeper/stim_backend.py
from __future__ import annotations
from typing import List, Tuple, Optional
import stim

from qminesweeper.quantum_backend import QuantumBackend, StabilizerQuantumState


class StimState(StabilizerQuantumState):
    """Stim-based stabilizer simulation backend."""

    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    def _init_state(self) -> None:
        self.tab = stim.TableauSimulator()
        self.tab.set_num_qubits(self.n)

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

    def measure(self, idx: int) -> int:
        return int(self.tab.measure(idx))

    def apply_gate(self, gate: str, targets: List[int]) -> None:
        op = StimBackend.gate_name_map.get(gate)
        if op is None:
            raise ValueError(f"Unsupported gate for Stim: {gate}")
        instr = op + " " + " ".join(str(t) for t in targets)
        self.tab.do(stim.Circuit(instr))


class StimBackend(QuantumBackend):
    """Factory that creates Stim stabilizer states."""

    gate_name_map = {
            "X": "X", "Y": "Y", "Z": "Z",
            "H": "H", "S": "S", "Sdg": "S_DAG",
            "SX": "SQRT_X", "SXdg": "SQRT_X_DAG",
            "SY": "SQRT_Y", "SYdg": "SQRT_Y_DAG",
            "CX": "CX", "CY": "CY", "CZ": "CZ", "SWAP": "SWAP",
        }

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
            "H": 1, "S": 1, "S_DAG": 1,
            "X": 1, "Y": 1, "Z": 1,
            "CX": 2, "CY": 2, "CZ": 2, "SWAP": 2,
        }
        name_map = {"S_DAG": "Sdg"}  # map Stim to your board conventions

        out: list[tuple[str, list[int]]] = []
        for inst in circuit:
            name = inst.name.upper()
            if name not in ARITY:
                continue

            name = name_map.get(name, name)
            arity = ARITY[name]

            # collect only real qubit indices
            qubits = [t.value for t in inst.targets_copy() if t.is_qubit_target]

            # sanity: Stim sometimes emits packed targets, split correctly
            if len(qubits) % arity != 0:
                raise ValueError(f"Unexpected arity for {name}: {qubits}")

            for i in range(0, len(qubits), arity):
                out.append((name, qubits[i:i+arity]))

        return out