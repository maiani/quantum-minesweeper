import pytest
import numpy as np
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import (
    QMineSweeperGame, GameConfig,
    WinCondition, MoveSet, GameStatus
)
from qminesweeper.stim_backend import StimBackend


def test_loss_on_bomb():
    board = QMineSweeperBoard(3, 3, StimBackend())
    board.span_classical_bombs(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.IDENTIFY, MoveSet.CLASSIC))

    expZ = board.board_expectations("Z")
    bomb = next(((r, c) for r in range(3) for c in range(3) if expZ[r, c] == -1))
    game.cmd_measure(*bomb)

    assert game.status == GameStatus.LOST


def test_win_classic_by_exploring_all_safe():
    board = QMineSweeperBoard(2, 2, StimBackend())
    board.span_classical_bombs(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.IDENTIFY, MoveSet.CLASSIC))

    expZ = board.board_expectations("Z")
    for r in range(2):
        for c in range(2):
            if expZ[r, c] == 1: 
                game.cmd_measure(r, c)

    assert game.status == GameStatus.WIN
    
def test_clear_condition_win():
    # Board with 1 bomb → clear it manually
    board = QMineSweeperBoard(1, 1, StimBackend())
    board.span_classical_bombs(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.CLEAR, MoveSet.CLASSIC))

    # No moves yet, should not be WIN
    assert game.status == GameStatus.ONGOING

    # After measuring a bomb, CLEAR condition should still be checked
    res = game.cmd_measure(0, 0)
    # In this trivial case, if probability = 0 after measurement, then WIN
    if np.allclose(board.bomb_probability_z(0), 0.0):
        assert game.status == GameStatus.WIN
    else:
        assert game.status in (GameStatus.ONGOING, GameStatus.LOST)


def test_sandbox_never_finishes():
    board = QMineSweeperBoard(2, 2, StimBackend())
    board.span_classical_bombs(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.SANDBOX, MoveSet.CLASSIC))

    # Measure a bomb → normally would lose
    res = game.cmd_measure(0, 0)
    assert game.status == GameStatus.ONGOING
    # Sandbox should never trigger WIN either
    for r in range(2):
        for c in range(2):
            game.cmd_measure(r, c)
    assert game.status == GameStatus.ONGOING
