"""Shared helpers for the chppy suite.

Deliberately dependency-light: numpy and pytest only, so this directory stays
runnable after the package is extracted to its own repository.
"""

from __future__ import annotations

import numpy as np
import pytest

# Single-qubit matrices for the whole supported vocabulary, used to build
# reference state vectors independently of the tableau implementation.
_ISQRT2 = 1.0 / np.sqrt(2.0)
GATE_MATRICES: dict[str, np.ndarray] = {
    "X": np.array([[0, 1], [1, 0]], complex),
    "Y": np.array([[0, -1j], [1j, 0]], complex),
    "Z": np.array([[1, 0], [0, -1]], complex),
    "H": np.array([[1, 1], [1, -1]], complex) * _ISQRT2,
    "S": np.array([[1, 0], [0, 1j]], complex),
    "Sdg": np.array([[1, 0], [0, -1j]], complex),
    "SX": np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], complex) / 2,
    "SXdg": np.array([[1 - 1j, 1 + 1j], [1 + 1j, 1 - 1j]], complex) / 2,
    "SY": np.array([[1 + 1j, -1 - 1j], [1 + 1j, 1 + 1j]], complex) / 2,
    "SYdg": np.array([[1 - 1j, 1 - 1j], [-1 + 1j, 1 - 1j]], complex) / 2,
}

PAULI_MATRICES: dict[str, np.ndarray] = {
    "I": np.eye(2, dtype=complex),
    "X": GATE_MATRICES["X"],
    "Y": GATE_MATRICES["Y"],
    "Z": GATE_MATRICES["Z"],
}


def apply_1q(vector: np.ndarray, matrix: np.ndarray, qubit: int, n: int) -> np.ndarray:
    """Apply a 2x2 matrix to `qubit` of an n-qubit state vector.

    Qubit 0 is the most significant tensor factor, matching the convention the
    library documents for its own indices.
    """
    out = vector.reshape([2] * n)
    out = np.moveaxis(out, qubit, 0).reshape(2, -1)
    out = matrix @ out
    return np.moveaxis(out.reshape([2] * n), 0, qubit).reshape(-1)


# Two-qubit gates as 4x4 matrices on the ordered pair (control, target), in the
# basis |00>, |01>, |10>, |11>.
TWO_QUBIT_MATRICES: dict[str, np.ndarray] = {
    "CX": np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
        complex,
    ),
    "CY": np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, -1j], [0, 0, 1j, 0]],
        complex,
    ),
    "CZ": np.diag([1, 1, 1, -1]).astype(complex),
    "SWAP": np.array(
        [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
        complex,
    ),
}


def apply_2q(vector: np.ndarray, name: str, a: int, b: int, n: int) -> np.ndarray:
    """Apply a supported two-qubit gate to a state vector.

    Moves the two targeted axes to the front so the 4x4 matrix acts on a plain
    (4, rest) reshape, then moves them back.
    """
    out = vector.reshape([2] * n)
    out = np.moveaxis(out, (a, b), (0, 1)).reshape(4, -1)
    out = TWO_QUBIT_MATRICES[name] @ out
    out = np.moveaxis(out.reshape([2] * n), (0, 1), (a, b))
    return out.reshape(-1)


def reference_state(circuit: list[tuple[str, list[int]]], n: int) -> np.ndarray:
    """Build the exact state vector for a circuit, starting from |0...0>."""
    vector = np.zeros(2**n, complex)
    vector[0] = 1.0
    for name, targets in circuit:
        if name in GATE_MATRICES:
            for target in targets:
                vector = apply_1q(vector, GATE_MATRICES[name], target, n)
        else:
            vector = apply_2q(vector, name, targets[0], targets[1], n)
    return vector


def reference_expectation(vector: np.ndarray, paulis: dict[int, str], n: int) -> float:
    """<P> for a tensor-product Pauli, computed from a state vector."""
    operator = np.array([1.0 + 0j])
    for qubit in range(n):
        operator = np.kron(operator, PAULI_MATRICES[paulis.get(qubit, "I")])
    return float(np.real(np.conjugate(vector) @ (operator @ vector)))


@pytest.fixture
def bell():
    """A freshly prepared two-qubit Bell state (|00> + |11>)/sqrt(2)."""
    from chppy import CHP

    sim = CHP(2)
    sim.apply_gate("H", [0])
    sim.apply_gate("CX", [0, 1])
    return sim
