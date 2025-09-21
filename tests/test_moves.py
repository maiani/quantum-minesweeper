# tests/test_moves.py
import pytest
from qminesweeper.board import QMineSweeperBoard, CellState
from qminesweeper.game import QMineSweeperGame, GameConfig, WinCondition, MoveSet
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend
from qminesweeper.qiskit_backend import QiskitBackend

@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_measure_and_explore(Backend : type[QuantumBackend]):
    board = QMineSweeperBoard(3, 3, Backend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.IDENTIFY, MoveSet.CLASSIC))

    expZ = board.board_expectations("Z")
    r, c = next(((r, c) for r in range(3) for c in range(3) if expZ[r, c] == 1))

    game.cmd_measure(r, c)
    state = board.exploration_state()
    assert state[r, c] == CellState.EXPLORED
