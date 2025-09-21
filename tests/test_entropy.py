# tests/test_entropy.py
import pytest
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend
from qminesweeper.qiskit_backend import QiskitBackend

@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_single_qubit_entropy_bounds(Backend : type[QuantumBackend]):
    b = QMineSweeperBoard(1, 1, Backend())
    b.span_classical_mines(0)  # |0>
    e0 = b.single_qubit_entropy(0)
    assert 0.0 <= e0 <= 1.0
    # Apply H -> |+>, still product, entropy ~0 (within fp noise)
    b.apply_gate("H", [(0,0)])
    e1 = b.single_qubit_entropy(0)
    assert e1 < 1e-9

@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_entropy_map_shape_and_aggregate(Backend : type[QuantumBackend]):
    b = QMineSweeperBoard(2, 3, Backend())
    b.span_random_stabilizer_mines(nmines=2, level=2)
    emap = b.entropy_map()
    assert emap.shape == (2,3)
    score = b.entanglement_score()
    assert 0.0 <= score <= 1.0
