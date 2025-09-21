# tests/test_board_init.py
import random

import numpy as np
import pytest

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend


def touched_indices(board: QMineSweeperBoard) -> list[int]:
    """
    Collect the set of qubit indices referenced by the board's *preparation circuit*.

    The sampler populates `board.preparation_circuit` with a sequence of (gate_name, targets),
    where `targets` is an iterable of *flat* qubit indices. This helper returns a sorted list
    of the unique indices that appear anywhere in that circuit.

    Parameters
    ----------
    board : QMineSweeperBoard
        The board whose preparation circuit we inspect.

    Returns
    -------
    list[int]
        Sorted unique qubit indices touched during preparation.
    """
    seen: set[int] = set()
    for name, targets in board.preparation_circuit:
        for t in targets:
            seen.add(int(t))
    return sorted(seen)


def test_classical_mine_count_still_exact() -> None:
    """
    Classical placement must touch exactly `nmines` distinct indices.
    (Sanity check for the non-quantum baseline.)
    """
    board = QMineSweeperBoard(4, 4, StimBackend())
    board.span_classical_mines(5)
    idxs = touched_indices(board)
    assert len(idxs) == 5


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_no_trivial_product_mines_level1(Backend: type[QuantumBackend]):
    """
    Level=1 stabilizer 'mines' are single-qubit stabilizers.
    We still require the sampler to avoid collapsing to the trivial |0...0> state
    on the touched indices (i.e., identity Clifford).
    """
    board = QMineSweeperBoard(4, 4, Backend())
    nb = 5
    board.span_random_stabilizer_mines(nmines=nb, level=1)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nmines indices"

    # If every touched index has <Z>=+1, that suggests |0...0> on that subset.
    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(float(expZ[i]) - 1.0) < 1e-9 for i in idxs), (
        "Group collapsed to |0...0> (identity Clifford), which should be excluded"
    )


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
@pytest.mark.parametrize("level", [1, 2, 3])
def test_group_levels_cover_indices(Backend: type[QuantumBackend], level: int):
    n = 5 if level == 3 else 4
    board = QMineSweeperBoard(n, n, Backend())
    nb = level * 2
    board.span_random_stabilizer_mines(nmines=nb, level=level)

    idxs = touched_indices(board)
    assert len(idxs) == nb
    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(float(expZ[i]) - 1.0) < 1e-9 for i in idxs)


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
@pytest.mark.parametrize("seed", list(range(10)))
def test_remainder_smaller_groups_still_exact_coverage(Backend: type[QuantumBackend], seed: list[int]):
    np.random.seed(seed)
    random.seed(seed)

    board = QMineSweeperBoard(6, 6, Backend())
    nb = 5
    board.span_random_stabilizer_mines(nmines=nb, level=3)

    idxs = touched_indices(board)
    assert len(idxs) == nb, f"{Backend.__name__}, seed={seed}, got {len(idxs)}"


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_randomness_varies(Backend: type[QuantumBackend]):
    """
    Sanity check that the sampler produces different states across runs.
    We collect the full Z-expectations board and require at least one pair
    of runs to differ (up to floating tolerance).
    """
    board = QMineSweeperBoard(3, 3, Backend())
    exps = []
    for _ in range(3):
        board.span_random_stabilizer_mines(nmines=3, level=2)
        exps.append(board.board_expectations("Z").copy())

    found_diff = any(not np.allclose(exps[i], exps[j]) for i in range(len(exps)) for j in range(i + 1, len(exps)))
    assert found_diff, "Sampler did not produce varied states across runs"
