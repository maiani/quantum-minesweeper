# tests/test_allowed_moves.py
import pytest
import numpy as np
from qminesweeper.board import QMineSweeperBoard, CellState
from qminesweeper.game import (
    QMineSweeperGame, GameConfig,
    WinCondition, MoveSet, GameStatus
)
from qminesweeper.stim_backend import StimBackend
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend

@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_pin_toggle_allowed(Backend : type[QuantumBackend]):
    board = QMineSweeperBoard(2, 2, Backend())
    board.span_classical_mines(1)

    for win_cond in [WinCondition.IDENTIFY, WinCondition.CLEAR]:
        for move_set in [MoveSet.CLASSIC, MoveSet.ONE_QUBIT, MoveSet.TWO_QUBIT]:
            game = QMineSweeperGame(board, GameConfig(win_cond, move_set))
            game.cmd_toggle_pin(0, 0)
            assert board.exploration_state()[0, 0] == CellState.PINNED
            game.cmd_toggle_pin(0, 0)
            assert board.exploration_state()[0, 0] == CellState.UNEXPLORED

@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_one_qubit_gate_allowed(Backend : type[QuantumBackend] ):
    board = QMineSweeperBoard(2, 2, Backend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.CLEAR, MoveSet.ONE_QUBIT))

    # Apply a Hadamard gate on (0,0). Should not raise.
    game.cmd_gate("H", [(0, 0)])
    assert game.status in (GameStatus.ONGOING, GameStatus.WIN)

@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_two_qubit_gate_allowed_only_in_two_qubit(Backend : type[QuantumBackend]):
    board = QMineSweeperBoard(2, 2, Backend())
    board.span_classical_mines(2)

    # Two-qubit gate should raise in ONE_QUBIT
    game1 = QMineSweeperGame(board, GameConfig(WinCondition.CLEAR, MoveSet.ONE_QUBIT))
    with pytest.raises(ValueError):
        game1.cmd_gate("CX", [(0, 0), (1, 1)])

    # Should succeed in TWO_QUBIT
    game2 = QMineSweeperGame(board, GameConfig(WinCondition.CLEAR, MoveSet.TWO_QUBIT))
    game2.cmd_gate("CX", [(0, 0), (1, 1)])
    assert game2.status in (GameStatus.ONGOING, GameStatus.WIN)
