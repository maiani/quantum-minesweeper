# qminesweeper/qiskit_backend.py
from __future__ import annotations
from typing import List
from qiskit import QuantumCircuit
from qiskit.quantum_info import StabilizerState, Pauli, Clifford
from qiskit.circuit.library import XGate, YGate, ZGate, HGate, SGate, CXGate

from qminesweeper.quantum_backend import QuantumBackend, StabilizerQuantumState


class QiskitState(StabilizerQuantumState):
    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    def _init_state(self):
        self.state = StabilizerState(QuantumCircuit(self.n))

    def reset(self) -> None:
        self._init_state()

    def expectation_pauli(self, idx: int, basis: str) -> float:
        """
        Return ⟨basis⟩ for a single qubit at index.
        basis ∈ {"X","Y","Z"}.
        """
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Basis must be one of 'X','Y','Z'")
        # Build Pauli string: leftmost = qubit 0 in Qiskit
        label = "I" * (self.n - idx - 1) + basis + "I" * idx
        value = self.state.expectation_value(Pauli(label))
        return float(value.real)

    def measure(self, idx: int) -> int:
        outcome, self.state = self.state.measure([idx])
        return int(outcome)

    def apply_gate(self, gate: str, targets: List[int]) -> None:
        gate_cls = {
            "X": XGate, "Y": YGate, "Z": ZGate,
            "H": HGate, "S": SGate, "CX": CXGate
        }.get(gate)
        if gate_cls is None:
            raise ValueError(f"Unsupported gate: {gate}")

        cl = Clifford(gate_cls())
        if cl.num_qubits != len(targets):
            raise ValueError(f"Gate {gate} expects {cl.num_qubits} qubits, got {len(targets)}")

        self.state = self.state.evolve(cl, targets)


class QiskitBackend(QuantumBackend):
    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        return QiskitState(n_qubits)
