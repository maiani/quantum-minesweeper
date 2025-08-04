from abc import ABC, abstractmethod
from typing import List


class QuantumBackend(ABC):
    """
    Abstract base class for all Quantum Minesweeper backends.
    Defines the interface that must be implemented.
    """

    def __init__(self, n_qubits: int):
        self.n = n_qubits

    @abstractmethod
    def expectation_z(self, idx: int) -> float:
        """
        Return the expectation value ⟨Z⟩ of Z for qubit idx.
        """
        pass

    @abstractmethod
    def measure(self, idx: int) -> int:
        """
        Measure qubit idx in the Z basis, return outcome (0 or 1),
        and collapse the state.
        """
        pass

    @abstractmethod
    def apply_gate(self, gate: str, targets: List[int]):
        """
        Apply a gate (as a string) to the given qubit(s).
        """
        pass
