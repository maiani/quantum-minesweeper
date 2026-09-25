# tests/test_exports.py
import numpy as np
import pytest

from qminesweeper.board import CellState, QMineSweeperBoard
from qminesweeper.chppy_backend import ChppyBackend
from qminesweeper.game import GameConfig, MoveSet, QMineSweeperGame, WinCondition
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, ChppyBackend])
def test_export_grid_values(Backend: type[QuantumBackend]):
    board = QMineSweeperBoard(2, 2, Backend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(win_condition=WinCondition.IDENTIFY, move_set=MoveSet.CLASSIC))

    grid = board.export_numeric_grid()
    assert (grid == -1).all()  # unexplored initially

    expZ = board.board_expectations("Z")
    safe = next(((r, c) for r in range(2) for c in range(2) if expZ[r, c] == 1))
    game.cmd_measure(*safe)

    grid = board.export_numeric_grid()
    assert grid[safe] >= 0  # clue shown


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, ChppyBackend])
def test_export_grid_matches_get_clue_on_an_entangled_board(Backend: type[QuantumBackend]):
    """The export reuses each cell's expectation; its values must not change."""
    np.random.seed(11)
    board = QMineSweeperBoard(5, 6, Backend(), flood_fill=True)
    board.span_random_stabilizer_mines(8, level=3)
    game = QMineSweeperGame(board, GameConfig(win_condition=WinCondition.SANDBOX, move_set=MoveSet.TWO_QUBIT))
    for r, c in [(0, 0), (2, 3), (4, 5), (1, 4), (3, 1)]:
        game.cmd_measure(r, c)
    board.toggle_pin(4, 0)

    grid = board.export_numeric_grid()
    state = board.exploration_state()
    for r in range(board.rows):
        for c in range(board.cols):
            if state[r, c] == CellState.EXPLORED:
                assert grid[r, c] == board.get_clue(r, c)
            elif state[r, c] == CellState.PINNED:
                assert grid[r, c] == -2.0
            else:
                assert grid[r, c] == -1.0
