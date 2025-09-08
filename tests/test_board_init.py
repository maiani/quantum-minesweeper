import numpy as np
from quantum_board import QMineSweeperGame, GameMode
from stim_backend import StimBackend

def make_classical(rows=5, cols=5, bombs=3):
    game = QMineSweeperGame(rows, cols, GameMode.CLASSIC, StimBackend())
    game.span_classical_bombs(bombs)
    return game

def test_classical_bomb_count():
    game = make_classical(4, 4, 5)
    expZ = game.board_expectations("Z")
    bombs = (1 - expZ) / 2
    # total bomb probability = #bombs
    assert np.isclose(bombs.sum(), 5)
