import numpy as np
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.stim_backend import StimBackend

def touched_indices(board: QMineSweeperBoard):
    """Return sorted list of unique qubit indices referenced by the prep circuit."""
    seen = set()
    for name, targets in board.preparation_circuit:
        for t in targets:
            seen.add(int(t))
    return sorted(seen)

def test_classical_bomb_count_still_exact():
    board = QMineSweeperBoard(4, 4, StimBackend())
    board.span_classical_bombs(5)
    idxs = touched_indices(board)
    assert len(idxs) == 5, "Classical bomb placement must touch exactly nbombs indices"

def test_no_trivial_product_bombs_level1():
    board = QMineSweeperBoard(4, 4, StimBackend())
    nb = 5
    board.span_random_stabilizer_bombs(nbombs=nb, level=1)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices"

    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(expZ[i] - 1.0) < 1e-9 for i in idxs), "Group collapsed to |0...0>"

def test_level2_groups_touch_exact_indices():
    board = QMineSweeperBoard(4, 4, StimBackend())
    nb = 4
    board.span_random_stabilizer_bombs(nbombs=nb, level=2)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices at level=2"

    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(expZ[i] - 1.0) < 1e-9 for i in idxs), "All-touched were |0…0>, which should be excluded"

def test_level3_groups_touch_exact_indices():
    board = QMineSweeperBoard(5, 5, StimBackend())
    nb = 6
    board.span_random_stabilizer_bombs(nbombs=nb, level=3)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices at level=3"

    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(expZ[i] - 1.0) < 1e-9 for i in idxs), "All-touched were |0…0>, which should be excluded"

def test_remainder_smaller_groups_still_exact_coverage():
    board = QMineSweeperBoard(5, 5, StimBackend())
    nb = 5   # level=2 -> two pairs + one single
    board.span_random_stabilizer_bombs(nbombs=nb, level=2)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices with remainder handling"

def test_randomness_varies():
    board = QMineSweeperBoard(3, 3, StimBackend())

    exps = []
    for _ in range(3):
        board.span_random_stabilizer_bombs(nbombs=3, level=2)
        exps.append(board.board_expectations("Z").copy())

    # Ensure at least one pair differs
    found_diff = any(not np.allclose(exps[i], exps[j])
                     for i in range(len(exps)) for j in range(i + 1, len(exps)))
    assert found_diff, "Sampler did not produce varied states across runs"
