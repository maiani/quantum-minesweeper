# ./src/quantum_backend.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, ClassVar


class StabilizerQuantumState(ABC):
    """Runtime quantum state handle used by the board."""
    ALLOWED_GATES: ClassVar[List[str]] = ["X", "Y", "Z", "H", "S", "CX"]

    @abstractmethod
    def expectation_pauli(self, idx: int, basis: str) -> float:
        """
        Return the expectation value ⟨basis⟩ for a single-qubit Pauli operator
        acting on qubit `idx`.

        Parameters
        ----------
        idx : int
            Index of the qubit.
        basis : str
            One of {"X", "Y", "Z"}.
        """
        ...

    @abstractmethod
    def measure(self, idx: int) -> int:
        """Projectively measure qubit `idx` in the Z basis and return the outcome (0 or 1)."""
        ...

    @abstractmethod
    def apply_gate(self, gate: str, targets: List[int]) -> None:
        """Apply a gate (must be in ALLOWED_GATES) to the specified targets."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset to |0>^n (same number of qubits as created)."""
        ...


class QuantumBackend(ABC):
    """Factory that creates a fresh stabilizer state for n qubits."""
    @abstractmethod
    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        ...
