from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import QMineSweeperGame, GameConfig, WinCondition, MoveSet, GameStatus
from qminesweeper.stim_backend import StimBackend

def test_loss_on_bomb():
    board = QMineSweeperBoard(3, 3, StimBackend())
    board.span_classical_bombs(1)
    game = QMineSweeperGame(board, GameConfig(WinCondition.IDENTIFY, MoveSet.CLASSIC))

    expZ = board.board_expectations("Z")
    bomb = next(((r, c) for r in range(3) for c in range(3) if expZ[r, c] == -1))
    game.cmd_measure(*bomb)

    assert game.status == GameStatus.LOSE

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
