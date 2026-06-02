# tests/test_moves.py
import pytest

from qminesweeper.board import CellState, QMineSweeperBoard
from qminesweeper.game import GameConfig, MoveSet, QMineSweeperGame, WinCondition
from qminesweeper.purepy_backend import PurePyBackend
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, PurePyBackend])
def test_measure_and_explore(Backend: type[QuantumBackend]):
    board = QMineSweeperBoard(3, 3, Backend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.IDENTIFY, MoveSet.CLASSIC))

    expZ = board.board_expectations("Z")
    r, c = next(((r, c) for r in range(3) for c in range(3) if expZ[r, c] == 1))

    game.cmd_measure(r, c)
    state = board.exploration_state()
    assert state[r, c] == CellState.EXPLORED


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend, PurePyBackend])
def test_gate_rejects_explored_cell_without_hiding_it(Backend: type[QuantumBackend]):
    board = QMineSweeperBoard(2, 2, Backend(), flood_fill=False)
    board.span_classical_mines(0)
    game = QMineSweeperGame(board, GameConfig(WinCondition.SANDBOX, MoveSet.ONE_QUBIT))

    game.cmd_measure(0, 0)
    assert board.exploration_state()[0, 0] == CellState.EXPLORED
    assert board.export_numeric_grid()[0, 0] == 0.0

    with pytest.raises(ValueError, match="Cannot apply gates to explored cells"):
        game.cmd_gate("X", [(0, 0)])

    assert board.exploration_state()[0, 0] == CellState.EXPLORED
    assert board.export_numeric_grid()[0, 0] == 0.0
