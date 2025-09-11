# tests/test_exports.py 
from qminesweeper.quantum_board import QMineSweeperGame, GameMode, CellState
from qminesweeper.stim_backend import StimBackend

def test_export_grid_values():
    game = QMineSweeperGame(2, 2, GameMode.CLASSIC, StimBackend())
    game.span_classical_bombs(1)

    grid = game.export_grid()
    assert (grid == -1).all()  # unexplored initially

    # measure one safe cell
    expZ = game.board_expectations("Z")
    safe = [(r, c) for r in range(2) for c in range(2) if expZ[r, c] == 1][0]
    game.measure(*safe)

    grid = game.export_grid()
    assert grid[safe] >= 0  # clue shown
