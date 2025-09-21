# tests/test_backends.py
import pytest
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend
from qminesweeper.qiskit_backend import QiskitBackend


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_random_clifford_circuit_nonempty(Backend : type[QuantumBackend]):
    """Every backend must return a nonempty circuit for n>0."""
    backend = Backend()
    circ = backend.random_clifford_circuit(3)
    assert isinstance(circ, list)
    assert len(circ) > 0, f"{Backend.__name__} produced an empty circuit!"


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_random_clifford_circuit_gate_format(Backend : type[QuantumBackend]):
    """Gate format must be (str, list[int]) with valid indices."""
    backend = Backend()
    n = 4
    circ = backend.random_clifford_circuit(n)
    for gate, targets in circ:
        assert isinstance(gate, str)
        assert isinstance(targets, list)
        assert all(isinstance(t, int) for t in targets)
        assert all(0 <= t < n for t in targets)


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_random_clifford_circuit_varies(Backend : type[QuantumBackend] ):
    """Two random circuits should differ with high probability."""
    backend = Backend()
    circ1 = backend.random_clifford_circuit(3)
    circ2 = backend.random_clifford_circuit(3)
    assert circ1 != circ2, f"{Backend.__name__} returned identical random circuits (unlikely)."


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
@pytest.mark.parametrize("n", [1, 2, 5, 10])
def test_random_clifford_circuit_scaling(Backend : type[QuantumBackend], n : int):
    """Backend must work across different qubit counts."""
    backend = Backend()
    circ = backend.random_clifford_circuit(n)
    assert all(0 <= t < n for _, targets in circ for t in targets)
