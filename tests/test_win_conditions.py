import pytest
import numpy as np
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import (
    QMineSweeperGame, GameConfig,
    WinCondition, MoveSet, GameStatus
)
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend
from qminesweeper.qiskit_backend import QiskitBackend

@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_loss_on_mine(Backend : type[QuantumBackend]):
    board = QMineSweeperBoard(3, 3, StimBackend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.IDENTIFY, MoveSet.CLASSIC))

    expZ = board.board_expectations("Z")
    mine = next(((r, c) for r in range(3) for c in range(3) if expZ[r, c] == -1))
    game.cmd_measure(*mine)

    assert game.status == GameStatus.LOST


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_win_classic_by_exploring_all_safe(Backend : type[QuantumBackend]):
    board = QMineSweeperBoard(2, 2, Backend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.IDENTIFY, MoveSet.CLASSIC))

    expZ = board.board_expectations("Z")
    for r in range(2):
        for c in range(2):
            if expZ[r, c] == 1: 
                game.cmd_measure(r, c)

    assert game.status == GameStatus.WIN
 
@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])   
def test_clear_condition_win(Backend : type[QuantumBackend]):
    # Board with 1 mine → clear it manually
    board = QMineSweeperBoard(1, 1, Backend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.CLEAR, MoveSet.CLASSIC))

    # No moves yet, should not be WIN
    assert game.status == GameStatus.ONGOING

    # After measuring a mine, CLEAR condition should still be checked
    res = game.cmd_measure(0, 0)
    # In this trivial case, if probability = 0 after measurement, then WIN
    if np.allclose(board.mine_probability_z(0), 0.0):
        assert game.status == GameStatus.WIN
    else:
        assert game.status in (GameStatus.ONGOING, GameStatus.LOST)


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_sandbox_never_finishes(Backend : type[QuantumBackend]):
    board = QMineSweeperBoard(2, 2, Backend())
    board.span_classical_mines(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.SANDBOX, MoveSet.CLASSIC))

    # Measure a mine → normally would lose
    res = game.cmd_measure(0, 0)
    assert game.status == GameStatus.ONGOING
    # Sandbox should never trigger WIN either
    for r in range(2):
        for c in range(2):
            game.cmd_measure(r, c)
    assert game.status == GameStatus.ONGOING
