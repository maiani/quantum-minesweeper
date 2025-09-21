# qminesweeper/quantum_backend.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional


class StabilizerQuantumState(ABC):
    """Runtime quantum state handle used by the board."""

    @abstractmethod
    def expectation_pauli(self, idx: int, basis: str) -> float:
        """Return ⟨basis⟩ for qubit `idx`, where basis ∈ {'X','Y','Z'}."""
        ...

    @abstractmethod
    def measure(self, idx: int) -> int:
        """Projectively measure qubit `idx` in the Z basis and return 0/1."""
        ...

    @abstractmethod
    def apply_gate(self, gate: str, targets: List[int]) -> None:
        """
        Apply a named gate to the specified targets.
        Gate vocabulary must match what backends emit in random_clifford_circuit.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset to |0⟩^n (same number of qubits as created)."""
        ...


class QuantumBackend(ABC):
    """Factory that creates a fresh stabilizer state for n qubits, plus utilities."""

    @abstractmethod
    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        """Create a new, reset stabilizer state with `n_qubits` wires."""
        ...

    @abstractmethod
    def random_clifford_circuit(self, k: int, *, seed: Optional[int] = None) -> List[Tuple[str, List[int]]]:
        """
        Return a random k-qubit Clifford as a **local** circuit:
        a list of (gate_name, local_targets) with local_targets in 0..k-1.

        The returned gate names MUST be in the vocabulary accepted by
        StabilizerQuantumState.apply_gate (e.g., 'X','Y','Z','H','S','Sdg',
        'SX','SXdg','SY','SYdg','CX','CY','CZ','SWAP').

        Implementations are free to choose any (reasonable) decomposition.
        """
        ...
