# ./src/quantum_backend.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, ClassVar


class StabilizerQuantumState(ABC):
    """Runtime quantum state handle used by the board."""
    ALLOWED_GATES: ClassVar[List[str]] = ["X", "Y", "Z", "H", "S", "CX"]

    @abstractmethod
    def expectation_z(self, idx: int) -> float: ...
    @abstractmethod
    def measure(self, idx: int) -> int: ...
    @abstractmethod
    def apply_gate(self, gate: str, targets: List[int]) -> None: ...
    @abstractmethod
    def reset(self) -> None:
        """Reset to |0>^n (same number of qubits as created)."""
        ...


class QuantumBackend(ABC):
    """Factory that creates a fresh stabilizer state for n qubits."""
    @abstractmethod
    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState: ...
