# tests/test_span_random_stabilizer_bombs.py
import numpy as np
import pytest

from quantum_board import QMineSweeperGame, GameMode
from stim_backend import StimBackend


def touched_indices(game: QMineSweeperGame):
    """Return sorted list of unique qubit indices referenced by the prep circuit."""
    seen = set()
    for name, targets in game.preparation_circuit:
        for t in targets:
            seen.add(int(t))
    return sorted(seen)


def test_classical_bomb_count_still_exact():
    """Classical spanner should flip exactly the requested number of positions."""
    game = QMineSweeperGame(4, 4, GameMode.CLASSIC, StimBackend())
    game.span_classical_bombs(5)

    idxs = touched_indices(game)
    assert len(idxs) == 5, "Classical bomb placement must touch exactly nbombs indices"


def test_no_trivial_product_bombs_level1():
    """Level=1 random stabilizers: exactly nbombs indices, none equals |0>."""
    game = QMineSweeperGame(4, 4, GameMode.CLASSIC, StimBackend())
    nb = 5
    game.span_random_stabilizer_bombs(nbombs=nb, level=1)

    idxs = touched_indices(game)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices"

    # Exclude |0>: for any touched index, <Z> must not be +1
    expZ = game.board_expectations("Z").ravel()
    assert not all(abs(expZ[i] - 1.0) < 1e-9 for i in idxs), "Group collapsed to |0...0>"


def test_level2_groups_touch_exact_indices():
    """Level=2: we don't assert 'bomb counts'—just that exactly nbombs indices are used."""
    game = QMineSweeperGame(4, 4, GameMode.CLASSIC, StimBackend())
    nb = 4
    game.span_random_stabilizer_bombs(nbombs=nb, level=2)

    idxs = touched_indices(game)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices at level=2"

    # Not all touched qubits may be |0>. This guards against accidental identity groups.
    expZ = game.board_expectations("Z").ravel()
    assert not all(abs(expZ[i] - 1.0) < 1e-9 for i in idxs), "All-touched were |0…0>, which should be excluded"


def test_level3_groups_touch_exact_indices():
    game = QMineSweeperGame(5, 5, GameMode.CLASSIC, StimBackend())
    nb = 6
    game.span_random_stabilizer_bombs(nbombs=nb, level=3)

    idxs = touched_indices(game)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices at level=3"

    expZ = game.board_expectations("Z").ravel()
    assert not all(abs(expZ[i] - 1.0) < 1e-9 for i in idxs), "All-touched were |0…0>, which should be excluded"


def test_remainder_smaller_groups_still_exact_coverage():
    """If nbombs not divisible by level, remainder should still give exact coverage."""
    game = QMineSweeperGame(5, 5, GameMode.CLASSIC, StimBackend())
    nb = 5   # level=2 -> two pairs + one single
    game.span_random_stabilizer_bombs(nbombs=nb, level=2)

    idxs = touched_indices(game)
    assert len(idxs) == nb, "Sampler must touch exactly nbombs indices with remainder handling"


def test_randomness_varies():
    """Basic sanity: multiple draws should produce different board expectations."""
    game = QMineSweeperGame(3, 3, GameMode.CLASSIC, StimBackend())

    exps = []
    for _ in range(3):
        game.span_random_stabilizer_bombs(nbombs=3, level=2)
        exps.append(game.board_expectations("Z").copy())

    # Ensure at least one pair differs
    found_diff = any(not np.allclose(exps[i], exps[j])
                     for i in range(len(exps)) for j in range(i + 1, len(exps)))
    assert found_diff, "Sampler did not produce varied states across runs"
