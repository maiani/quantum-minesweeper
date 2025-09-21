"""
Property-based-ish tests for the random stabilizer mine sampler.

What we verify:
- Exact coverage: the preparation circuit must reference exactly `nmines`
  unique qubit indices (no drops / duplicates).
- Non-triviality: exclude the trivial all-|0...0> (identity Clifford) case.
- Grouping logic at different `level`s (1, 2, 3) produces the expected
  number of touched indices.
- Remainder handling: when nmines is not a multiple of `level`, the
  leftovers must still be covered (never dropped).
- Randomness: repeated sampling produces different expectation grids.

Notes on the “fuzzy” test:
- `test_remainder_smaller_groups_still_exact_coverage` is parameterized
  over many seeds to catch heisenbugs / flakiness. If a specific seed
  exposes a bug, the assertion message prints the seed so the failure
  is perfectly reproducible.
"""

from __future__ import annotations

import random
from typing import List

import numpy as np
import pytest

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.stim_backend import StimBackend


def touched_indices(board: QMineSweeperBoard) -> List[int]:
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
    List[int]
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
    assert len(idxs) == 5, "Classical mine placement must touch exactly nmines indices"


def test_no_trivial_product_mines_level1() -> None:
    """
    Level=1 stabilizer 'mines' are single-qubit stabilizers.
    We still require the sampler to avoid collapsing to the trivial |0...0> state
    on the touched indices (i.e., identity Clifford).
    """
    board = QMineSweeperBoard(4, 4, StimBackend())
    nb = 5
    board.span_random_stabilizer_mines(nmines=nb, level=1)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nmines indices"

    # If every touched index has <Z>=+1, that suggests |0...0> on that subset.
    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(float(expZ[i]) - 1.0) < 1e-9 for i in idxs), \
        "Group collapsed to |0...0> (identity Clifford), which should be excluded"


def test_level2_groups_touch_exact_indices() -> None:
    """
    For level=2, the sampler should build two-qubit blocks and still cover the
    requested number of distinct indices.
    """
    board = QMineSweeperBoard(4, 4, StimBackend())
    nb = 4
    board.span_random_stabilizer_mines(nmines=nb, level=2)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nmines indices at level=2"

    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(float(expZ[i]) - 1.0) < 1e-9 for i in idxs), \
        "All-touched were |0…0>, which should be excluded"


def test_level3_groups_touch_exact_indices() -> None:
    """
    For level=3, the sampler should build three-qubit blocks and still cover the
    requested number of distinct indices.
    """
    board = QMineSweeperBoard(5, 5, StimBackend())
    nb = 6
    board.span_random_stabilizer_mines(nmines=nb, level=3)

    idxs = touched_indices(board)
    assert len(idxs) == nb, "Sampler must touch exactly nmines indices at level=3"

    expZ = board.board_expectations("Z").ravel()
    assert not all(abs(float(expZ[i]) - 1.0) < 1e-9 for i in idxs), \
        "All-touched were |0…0>, which should be excluded"


@pytest.mark.parametrize("seed", list(range(500)))
def test_remainder_smaller_groups_still_exact_coverage(seed: int) -> None:
    """
    Hammer remainder handling with many seeds:
    - level=3 with nmines=5 should produce blocks like 3 + 2 (or 3 + 1 + 1),
      but in any case must cover exactly 5 distinct indices.
    - If a bug drops the leftover(s), this test will fail for some seed and
      report it, making the issue reproducible.

    We seed both NumPy and Python's PRNG to keep failures reproducible.
    """
    np.random.seed(seed)
    random.seed(seed)

    board = QMineSweeperBoard(6, 6, StimBackend())
    nb = 5
    board.span_random_stabilizer_mines(nmines=nb, level=3)

    idxs = touched_indices(board)
    assert len(idxs) == nb, f"seed={seed}: expected {nb}, got {len(idxs)}; idxs={idxs}"


def test_randomness_varies() -> None:
    """
    Sanity check that the sampler produces different states across runs.
    We collect the full Z-expectations board and require at least one pair
    of runs to differ (up to floating tolerance).
    """
    board = QMineSweeperBoard(3, 3, StimBackend())

    exps: list[np.ndarray] = []
    for _ in range(3):
        board.span_random_stabilizer_mines(nmines=3, level=2)
        exps.append(board.board_expectations("Z").copy())

    # Ensure at least one pair of runs differs
    found_diff = any(
        not np.allclose(exps[i], exps[j])
        for i in range(len(exps)) for j in range(i + 1, len(exps))
    )
    assert found_diff, "Sampler did not produce varied states across runs"
