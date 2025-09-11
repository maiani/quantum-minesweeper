# tests/test_moves.py
from qminesweeper.quantum_board import QMineSweeperGame, GameMode, MoveType, CellState
from qminesweeper.stim_backend import StimBackend

def test_measure_and_explore():
    game = QMineSweeperGame(3, 3, GameMode.CLASSIC, StimBackend())
    game.span_classical_bombs(1)

    # pick a non-bomb cell
    expZ = game.board_expectations("Z")
    safe = [(r, c) for r in range(3) for c in range(3) if expZ[r, c] == 1][0]
    r, c = safe

    game.move(MoveType.MEASURE, (r, c))
    assert game.exploration_state[r, c] == CellState.EXPLORED
