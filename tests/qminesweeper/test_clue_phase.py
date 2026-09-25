"""The clue phase: the transverse part of a clue's neighbourhood Bloch sum.

A clue's number is the sum of its neighbours' Z-basis mine probabilities. Its
colour is drawn from the rest of the same vector sum, (Σ⟨X⟩, Σ⟨Y⟩), so a phase
gate on a neighbour, which leaves every number unchanged, still shows.
"""

from __future__ import annotations

import numpy as np
import pytest

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.chppy_backend import ChppyBackend
from qminesweeper.engine import serialize_game
from qminesweeper.game import GameConfig, MoveSet, QMineSweeperGame, WinCondition
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend

BACKENDS = [StimBackend, QiskitBackend, ChppyBackend]


def _center_clue_board(Backend: type[QuantumBackend]) -> tuple[QMineSweeperBoard, QMineSweeperGame]:
    """A 3x3 board with no mines and only its centre explored."""
    board = QMineSweeperBoard(3, 3, Backend(), flood_fill=False)
    board.span_classical_mines(0)
    game = QMineSweeperGame(board, GameConfig(WinCondition.SANDBOX, MoveSet.TWO_QUBIT_EXTENDED))
    game.cmd_measure(1, 1)
    return board, game


def _center(board: QMineSweeperBoard) -> tuple[float, tuple[float, float]]:
    """The centre's clue and its (Σ⟨X⟩, Σ⟨Y⟩), rounded against backend round-off."""
    clue = board.export_numeric_grid()[1, 1]
    x, y = board.export_clue_phase_grid()[1, 1]
    return round(float(clue), 9), (round(float(x), 9) + 0.0, round(float(y), 9) + 0.0)


@pytest.mark.parametrize("Backend", BACKENDS)
def test_phase_gates_change_the_phase_but_not_the_number(Backend):
    board, game = _center_clue_board(Backend)
    assert _center(board) == (0.0, (0.0, 0.0))

    game.cmd_gate("H", [(0, 0)])  # |+>
    assert _center(board) == (0.5, (1.0, 0.0))
    game.cmd_gate("S", [(0, 0)])  # |+> -> |i>: a quarter turn
    assert _center(board) == (0.5, (0.0, 1.0))
    game.cmd_gate("Z", [(0, 0)])  # |i> -> |-i>: a half turn
    assert _center(board) == (0.5, (0.0, -1.0))
    game.cmd_gate("Sdg", [(0, 0)])  # |-i> -> |->
    assert _center(board) == (0.5, (-1.0, 0.0))


@pytest.mark.parametrize("Backend", BACKENDS)
def test_phases_add_and_cancel_across_neighbours(Backend):
    board, game = _center_clue_board(Backend)
    game.cmd_gate("H", [(0, 0), (0, 1)])  # two |+> neighbours add up
    assert _center(board) == (1.0, (2.0, 0.0))
    game.cmd_gate("Z", [(0, 1)])  # |+> and |->: opposite phases cancel
    assert _center(board) == (1.0, (0.0, 0.0))


@pytest.mark.parametrize("Backend", BACKENDS)
def test_an_entangled_neighbour_carries_no_phase(Backend):
    """Its reduced state is mixed: the 0.5 is there, the direction is not."""
    board, game = _center_clue_board(Backend)
    game.cmd_gate("H", [(0, 0)])
    game.cmd_gate("CX", [(0, 0), (2, 2)])  # a Bell pair across the centre
    assert _center(board) == (1.0, (0.0, 0.0))


@pytest.mark.parametrize("Backend", BACKENDS)
def test_cells_without_a_clue_have_no_phase(Backend):
    board, game = _center_clue_board(Backend)
    game.cmd_gate("H", [(0, 0), (2, 0)])
    board.toggle_pin(2, 0)
    phase = board.export_clue_phase_grid()
    mask = np.ones((3, 3), dtype=bool)
    mask[1, 1] = False
    assert (phase[mask] == 0.0).all()


def test_a_definite_mine_shows_no_phase():
    board = QMineSweeperBoard(2, 2, ChppyBackend(), flood_fill=False)
    board.set_preparation([("X", [0]), ("H", [1])])
    board.reset()
    board._exploration[0, 0] = 2  # revealed mine: the lost-game view
    assert board.export_numeric_grid()[0, 0] == 9.0
    assert board.export_clue_phase_grid()[0, 0].tolist() == [0.0, 0.0]


@pytest.mark.parametrize("Backend", BACKENDS)
def test_shared_bloch_vectors_match_per_query_values_exactly(Backend):
    """serialize_game reads the state once; every observable must be unchanged."""
    np.random.seed(21)
    board = QMineSweeperBoard(4, 5, Backend(), flood_fill=True)
    board.span_random_stabilizer_mines(6, level=2)
    game = QMineSweeperGame(board, GameConfig(WinCondition.SANDBOX, MoveSet.TWO_QUBIT_EXTENDED))
    for r, c in [(0, 0), (3, 4), (1, 2)]:
        game.cmd_measure(r, c)
    bloch = board.bloch_vectors()

    assert np.array_equal(board.export_numeric_grid(bloch), board.export_numeric_grid())
    assert np.array_equal(board.export_clue_phase_grid(bloch), board.export_clue_phase_grid())
    assert board.expected_mines(bloch) == board.expected_mines()
    assert board.entanglement_score("mean", bloch) == board.entanglement_score("mean")
    state = serialize_game(board, game, "g")
    assert state["grid"] == board.export_numeric_grid().tolist()
    assert state["mines_exp"] == board.expected_mines()
