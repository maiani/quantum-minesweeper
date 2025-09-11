# tests/test_status.py
from qminesweeper.quantum_board import QMineSweeperGame, GameMode
from qminesweeper.stim_backend import StimBackend

def test_loss_on_bomb():
    game = QMineSweeperGame(3, 3, GameMode.CLASSIC, StimBackend())
    game.span_classical_bombs(1)

    expZ = game.board_expectations("Z")
    bomb = [(r, c) for r in range(3) for c in range(3) if expZ[r, c] == -1][0]
    game.measure(*bomb)

    assert game.game_status.name == "LOSE"

def test_win_classical():
    game = QMineSweeperGame(2, 2, GameMode.CLASSIC, StimBackend())
    game.span_classical_bombs(1)

    expZ = game.board_expectations("Z")
    for r in range(2):
        for c in range(2):
            if expZ[r, c] == 1:
                game.measure(r, c)

    assert game.game_status.name == "WIN"
