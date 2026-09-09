# tests/qminesweeper/test_backends.py
import numpy as np
import pytest

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.chppy_backend import ChppyBackend
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, ChppyBackend])
def test_random_clifford_circuit_nonempty(Backend: type[QuantumBackend]):
    """Every backend must return a nonempty circuit for n>0."""
    backend = Backend()
    circ = backend.random_clifford_circuit(3)
    assert isinstance(circ, list)
    assert len(circ) > 0, f"{Backend.__name__} produced an empty circuit!"


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, ChppyBackend])
def test_random_clifford_circuit_accepts_seed(Backend: type[QuantumBackend]):
    """Every backend must accept the ABC's `seed` keyword.

    Whether a backend honours the seed is per-backend (see "Simulator backends"
    in docs/architecture.md); accepting the keyword is not. This pins the
    signature so a backend cannot quietly drop it and raise TypeError on a
    caller that passes one, as StimBackend previously did.
    """
    circ = Backend().random_clifford_circuit(3, seed=1234)
    assert len(circ) > 0


# --- chppy seeding ---------------------------------------------------------
# Only ChppyBackend honours the seed. Stim cannot seed Tableau.random at all,
# and Qiskit honours it through random_clifford; see "Simulator backends" in
# docs/architecture.md. These tests pin chppy's own contract, which is
# in-backend reproducibility, not agreement with the other backends.


@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_chppy_same_seed_repeats_the_circuit(n: int):
    backend = ChppyBackend()
    assert backend.random_clifford_circuit(n, seed=4242) == backend.random_clifford_circuit(n, seed=4242)


def test_chppy_different_seeds_differ():
    backend = ChppyBackend()
    circuits = {tuple(map(str, backend.random_clifford_circuit(4, seed=s))) for s in range(8)}
    # Distinct seeds should not collapse onto one circuit.
    assert len(circuits) > 1


def test_chppy_seeded_call_leaves_the_global_stream_alone():
    """A seeded call must use its own generator, not the global one.

    Otherwise passing a seed would perturb the unseeded draws that
    span_random_stabilizer_mines and the golden export tests depend on.
    """
    backend = ChppyBackend()
    np.random.seed(17)
    expected = np.random.random()

    np.random.seed(17)
    backend.random_clifford_circuit(4, seed=999)
    assert np.random.random() == expected


def test_chppy_seed_matches_seeding_the_global_stream():
    """`seed=s` agrees with `np.random.seed(s)` then an unseeded call.

    RandomState(s) and the seeded global stream are the same sequence, so the
    seeded and unseeded paths cannot drift apart.
    """
    backend = ChppyBackend()
    np.random.seed(2024)
    unseeded = backend.random_clifford_circuit(4)
    assert backend.random_clifford_circuit(4, seed=2024) == unseeded


def test_chppy_unseeded_still_follows_the_global_stream():
    """The unseeded path stays reproducible under np.random.seed."""
    backend = ChppyBackend()
    np.random.seed(5)
    first = backend.random_clifford_circuit(3)
    np.random.seed(5)
    assert backend.random_clifford_circuit(3) == first


def test_chppy_seeded_boards_are_reproducible():
    """The seed reaches a prepared board when the caller pins the pool draw too.

    span_random_stabilizer_mines picks its mine indices from the global stream,
    so a reproducible board needs both that seed and the circuit seed. This
    documents the boundary rather than implying the circuit seed alone is enough.
    """
    backend = ChppyBackend()
    circuits, probabilities = [], []
    for _ in range(2):
        np.random.seed(31337)
        board = QMineSweeperBoard(3, 3, backend=backend, flood_fill=False)
        board.span_random_stabilizer_mines(4, level=2)
        circuits.append([(gate, list(targets)) for gate, targets in board.preparation_circuit])
        probabilities.append([board.mine_probability_z(i) for i in range(board.n)])
    assert circuits[0] == circuits[1]
    assert probabilities[0] == probabilities[1]


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, ChppyBackend])
def test_random_clifford_circuit_gate_format(Backend: type[QuantumBackend]):
    """Gate format must be (str, list[int]) with valid indices."""
    backend = Backend()
    n = 4
    circ = backend.random_clifford_circuit(n)
    for gate, targets in circ:
        assert isinstance(gate, str)
        assert isinstance(targets, list)
        assert all(isinstance(t, int) for t in targets)
        assert all(0 <= t < n for t in targets)


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, ChppyBackend])
def test_random_clifford_circuit_varies(Backend: type[QuantumBackend]):
    """Two random circuits should differ with high probability."""
    backend = Backend()
    circ1 = backend.random_clifford_circuit(3)
    circ2 = backend.random_clifford_circuit(3)
    assert circ1 != circ2, f"{Backend.__name__} returned identical random circuits (unlikely)."


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, ChppyBackend])
@pytest.mark.parametrize("n", [1, 2, 5, 10])
def test_random_clifford_circuit_scaling(Backend: type[QuantumBackend], n: int):
    """Backend must work across different qubit counts."""
    backend = Backend()
    circ = backend.random_clifford_circuit(n)
    assert all(0 <= t < n for _, targets in circ for t in targets)
