# ./src/stim_backend.py
from __future__ import annotations
from typing import List
import stim

from quantum_backend import QuantumBackend, StabilizerQuantumState


class StimState(StabilizerQuantumState):
    """Stim-based stabilizer simulation backend."""

    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    def _init_state(self):
        self.tableau = stim.TableauSimulator()
        self.tableau.set_num_qubits(self.n)

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

        pauli_string = ["I"] * self.n
        pauli_string[idx] = basis
        obs = stim.PauliString("".join(pauli_string))
        return self.tableau.peek_observable_expectation(obs)

    def measure(self, idx: int) -> int:
        """Projectively measure qubit in Z-basis."""
        return int(self.tableau.measure(idx))

    def apply_gate(self, gate: str, targets: List[int]) -> None:
        """
        Apply a Clifford gate.
        Supported: X, Y, Z, H, S, Sdg, SX, SXdg, SY, SYdg,
                CX, CY, CZ, SWAP
        """
        gate_map = {
            # Single-qubit
            "X": "X",
            "Y": "Y",
            "Z": "Z",
            "H": "H",
            "S": "S",
            "Sdg": "S_DAG",
            "SX": "SQRT_X",
            "SXdg": "SQRT_X_DAG",
            "SY": "SQRT_Y",
            "SYdg": "SQRT_Y_DAG",
            # Two-qubit
            "CX": "CX",
            "CY": "CY",
            "CZ": "CZ",
            "SWAP": "SWAP",
        }
        stim_gate = gate_map.get(gate)
        if stim_gate is None:
            raise ValueError(f"Unsupported gate: {gate}")

        # Build a tiny Stim circuit with the instruction
        instr = stim_gate + " " + " ".join(str(t) for t in targets)
        circuit = stim.Circuit(instr)
        self.tableau.do(circuit)


class StimBackend(QuantumBackend):
    """Factory that creates Stim stabilizer states."""

    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        return StimState(n_qubits)
