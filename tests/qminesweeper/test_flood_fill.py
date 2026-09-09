# tests/test_flood_fill.py
"""Direct flood-fill behaviour and coordinate bounds checking."""

from __future__ import annotations

import numpy as np
import pytest

from qminesweeper.board import CellState, QMineSweeperBoard
from qminesweeper.stim_backend import StimBackend


def _mine_free_board(rows=4, cols=4) -> QMineSweeperBoard:
    b = QMineSweeperBoard(rows, cols, backend=StimBackend(), flood_fill=True)
    b.span_classical_mines(0)
    b.set_clue_basis("Z")
    return b


def test_flood_fill_clears_whole_mine_free_board():
    """On a mine-free board every clue is 0, so one measure floods everything."""
    b = _mine_free_board(4, 4)
    res = b.measure_cell(0, 0)
    explored = b.exploration_state()
    assert np.all(explored == CellState.EXPLORED)
    assert len(res.explored) == 16


def test_flood_fill_stops_at_nonzero_clue():
    """A single mine in the corner gives its neighbors nonzero clues; flood must
    not reveal the mine itself and must stop at the clue frontier."""
    np.random.seed(7)
    b = QMineSweeperBoard(5, 5, backend=StimBackend(), flood_fill=True)
    # Place one classical mine at a known cell by preparing it directly.
    b.set_preparation([("X", [b.index(0, 0)])])
    b.reset()
    b.set_clue_basis("Z")

    # Measure far from the mine; flood should expand but never explore (0,0).
    b.measure_cell(4, 4)
    explored = b.exploration_state()
    assert explored[0, 0] != CellState.EXPLORED  # the mine stayed hidden
    # Cells adjacent to the mine have clue 1; they get explored but do not expand.
    assert explored[4, 4] == CellState.EXPLORED


def test_flood_fill_respects_pinned_cells():
    b = _mine_free_board(4, 4)
    b.toggle_pin(0, 1)
    b.measure_cell(0, 0)
    explored = b.exploration_state()
    assert explored[0, 1] == CellState.PINNED  # never flooded over


def test_index_out_of_bounds_raises():
    b = _mine_free_board(3, 3)
    for r, c in [(-1, 0), (0, -1), (3, 0), (0, 3), (3, 3)]:
        with pytest.raises(IndexError):
            b.index(r, c)


def test_measure_and_pin_reject_out_of_bounds():
    b = _mine_free_board(3, 3)
    with pytest.raises(IndexError):
        b.measure_cell(-1, -1)  # would otherwise wrap to the opposite corner
    with pytest.raises(IndexError):
        b.toggle_pin(-1, -1)
