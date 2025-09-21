# qminesweeper/qiskit_backend.py
from __future__ import annotations

from typing import List, Optional, Tuple

from qiskit import QuantumCircuit
from qiskit.circuit.library import (
    CXGate,
    CYGate,
    CZGate,
    HGate,
    SdgGate,
    SGate,
    SwapGate,
    SXGate,
    XGate,
    YGate,
    ZGate,
)
from qiskit.quantum_info import Clifford, Pauli, StabilizerState, random_clifford

from qminesweeper.quantum_backend import QuantumBackend, StabilizerQuantumState


class QiskitState(StabilizerQuantumState):
    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    def _init_state(self) -> None:
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
        gate_map = {
            "X": XGate,
            "Y": YGate,
            "Z": ZGate,
            "H": HGate,
            "S": SGate,
            "Sdg": SdgGate,
            "SX": SXGate,
            "CX": CXGate,
            "CY": CYGate,
            "CZ": CZGate,
            "SWAP": SwapGate,
        }
        gate_cls = gate_map.get(gate)
        if gate_cls is None:
            raise ValueError(f"Unsupported gate: {gate}")
        cl = Clifford(gate_cls())
        if cl.num_qubits != len(targets):
            raise ValueError(f"Gate {gate} expects {cl.num_qubits} qubits, got {len(targets)}")
        self.state = self.state.evolve(cl, targets)


class QiskitBackend(QuantumBackend):
    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        return QiskitState(n_qubits)

    def random_clifford_circuit(self, k: int, *, seed: Optional[int] = None) -> List[Tuple[str, List[int]]]:
        """
        Use Qiskit to sample a random k-qubit Clifford and convert to a local circuit.
        Gate names are normalized to the vocabulary accepted by QiskitState.apply_gate.
        """
        if k <= 0:
            return []
        cl = random_clifford(k, seed=seed)
        qc = cl.to_circuit()

        out: List[Tuple[str, List[int]]] = []
        for instr in qc.data:
            name = instr.operation.name.upper()
            if name == "SDG":
                name = "Sdg"  # canonicalize
            # Map qargs to local indices 0..k-1
            tloc = [qc.qubits.index(q) for q in instr.qubits]
            out.append((name, tloc))
        return out
