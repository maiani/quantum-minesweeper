# tests/test_exports_golden.py
"""
Golden snapshot of export_numeric_grid().

This pins the exact grid contract the (future) client-side renderer must
reproduce: the sentinel scheme (-1 unexplored, -2 pinned, 9 mine, 0..8 clue)
and integer clue counts on a deterministic classical board. If the contract
changes, this test must change with it — deliberately.
"""

from __future__ import annotations

import numpy as np

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.stim_backend import StimBackend

# Fully-explored 5x5 classical board, np.random.seed(1234), 5 mines, no flood-fill.
GOLDEN_GRID = [
    [1.0, 9.0, 9.0, 9.0, 1.0],
    [1.0, 3.0, 9.0, 3.0, 1.0],
    [1.0, 2.0, 2.0, 1.0, 0.0],
    [1.0, 9.0, 1.0, 0.0, 0.0],
    [1.0, 1.0, 1.0, 0.0, 0.0],
]


def _fully_explored_board() -> QMineSweeperBoard:
    np.random.seed(1234)
    b = QMineSweeperBoard(5, 5, backend=StimBackend(), flood_fill=False)
    b.span_classical_mines(5)
    b.set_clue_basis("Z")
    for r in range(5):
        for c in range(5):
            b.measure_cell(r, c)
    return b


def test_export_numeric_grid_golden():
    b = _fully_explored_board()
    assert b.export_numeric_grid().tolist() == GOLDEN_GRID


def test_export_numeric_grid_sentinels_initial():
    """A fresh board is all unexplored (-1)."""
    b = QMineSweeperBoard(3, 3, backend=StimBackend(), flood_fill=False)
    b.span_classical_mines(2)
    grid = b.export_numeric_grid()
    assert np.all(grid == -1.0)


def test_export_numeric_grid_pinned_sentinel():
    b = QMineSweeperBoard(3, 3, backend=StimBackend(), flood_fill=False)
    b.span_classical_mines(0)
    b.toggle_pin(1, 1)
    assert b.export_numeric_grid()[1, 1] == -2.0


def test_definite_mine_is_nine():
    """A measured classical |1> cell renders as the mine sentinel 9.0."""
    np.random.seed(1234)
    b = _fully_explored_board()
    assert GOLDEN_GRID == b.export_numeric_grid().tolist()
    assert (b.export_numeric_grid() == 9.0).sum() == 5
