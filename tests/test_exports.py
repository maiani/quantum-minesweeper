from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import QMineSweeperGame, GameConfig, WinCondition, MoveSet
from qminesweeper.stim_backend import StimBackend

def test_export_grid_values():
    board = QMineSweeperBoard(2, 2, StimBackend())
    board.span_classical_bombs(1)
    game = QMineSweeperGame(board, GameConfig(win_condition=WinCondition.IDENTIFY,
                                              move_set=MoveSet.CLASSIC))

    grid = board.export_numeric_grid()
    assert (grid == -1).all()  # unexplored initially

    expZ = board.board_expectations("Z")
    safe = next(((r, c) for r in range(2) for c in range(2) if expZ[r, c] == 1))
    game.cmd_measure(*safe)

    grid = board.export_numeric_grid()
    assert grid[safe] >= 0  # clue shown
