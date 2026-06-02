# tests/test_engine.py
"""The framework-free engine contract: serialize_game, parse_command, apply_command."""

from __future__ import annotations

import numpy as np
import pytest

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.engine import _SINGLE_Q, _TWO_Q, Command, apply_command, parse_command, serialize_game
from qminesweeper.game import GameConfig, GameStatus, MoveSet, QMineSweeperGame, WinCondition
from qminesweeper.stim_backend import StimBackend


def _game(rows=2, cols=2, mines=0, moveset=MoveSet.TWO_QUBIT_EXTENDED, win=WinCondition.SANDBOX, flood=False):
    board = QMineSweeperBoard(rows, cols, backend=StimBackend(), flood_fill=flood)
    board.span_classical_mines(mines)
    board.set_clue_basis("Z")
    return board, QMineSweeperGame(board, GameConfig(win, moveset))


# ---------- parse_command ----------
def test_parse_bare_coords_is_measure():
    assert parse_command("2,3") == Command("measure", cell=(1, 2))


def test_parse_measure_and_pin():
    assert parse_command("M 2,3") == Command("measure", cell=(1, 2))
    assert parse_command("P 4,4") == Command("pin", cell=(3, 3))


def test_parse_single_and_two_qubit_gate():
    assert parse_command("SDG 1,1") == Command("gate", gate="SDG", cell=(0, 0))
    assert parse_command("CX 1,1 2,2") == Command("gate", gate="CX", cell=(0, 0), cell2=(1, 1))


def test_parse_is_case_insensitive_on_op():
    assert parse_command("cx 1,1 2,2") == Command("gate", gate="CX", cell=(0, 0), cell2=(1, 1))


@pytest.mark.parametrize("bad", ["", "   ", "x", "M", "1,", ",2", "CX 1,1", "X 1,1 2,2", "FOO 1,1"])
def test_parse_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_command(bad)


# ---------- apply_command ----------
def test_apply_measure_explores_cell():
    board, game = _game()
    apply_command(board, game, parse_command("1,1"))
    from qminesweeper.board import CellState

    assert board.exploration_state()[0, 0] == CellState.EXPLORED


def test_apply_reset_restores_unexplored():
    board, game = _game(mines=0)
    apply_command(board, game, Command("measure", cell=(0, 0)))
    apply_command(board, game, Command("reset"))
    from qminesweeper.board import CellState

    assert np.all(board.exploration_state() == CellState.UNEXPLORED)
    assert game.status == GameStatus.ONGOING


@pytest.mark.parametrize("token", sorted(_SINGLE_Q))
def test_every_single_qubit_token_applies(token):
    """Regression: 'SDG'/'SXDG'/'SYDG' (and the rest) parse + apply cleanly."""
    board, game = _game()
    apply_command(board, game, parse_command(f"{token} 1,1"))  # must not raise


@pytest.mark.parametrize("token", sorted(_TWO_Q))
def test_every_two_qubit_token_applies(token):
    board, game = _game()
    apply_command(board, game, parse_command(f"{token} 1,1 1,2"))  # must not raise


def test_lowercase_gate_token_applies():
    board, game = _game()
    apply_command(board, game, parse_command("sdg 1,1"))  # must not raise


# ---------- serialize_game ----------
def test_serialize_game_golden():
    np.random.seed(1234)
    board = QMineSweeperBoard(5, 5, backend=StimBackend(), flood_fill=False)
    board.span_classical_mines(5)
    board.set_clue_basis("Z")
    for r in range(5):
        for c in range(5):
            board.measure_cell(r, c)
    game = QMineSweeperGame(board, GameConfig(WinCondition.SANDBOX, MoveSet.ONE_QUBIT))

    state = serialize_game(board, game, "gid-1")

    assert set(state) == {
        "game_id",
        "rows",
        "cols",
        "grid",
        "status",
        "win_condition",
        "moveset",
        "mines_exp",
        "ent_measure",
    }
    # No presentation/config leaks into the contract.
    for banned in ("features", "allowed_moves", "clue_color"):
        assert banned not in state
    assert state["game_id"] == "gid-1"
    assert state["rows"] == 5 and state["cols"] == 5
    assert state["status"] == "ONGOING"
    assert state["moveset"] == "ONE_QUBIT"
    assert state["grid"] == [
        [1.0, 9.0, 9.0, 9.0, 1.0],
        [1.0, 3.0, 9.0, 3.0, 1.0],
        [1.0, 2.0, 2.0, 1.0, 0.0],
        [1.0, 9.0, 1.0, 0.0, 0.0],
        [1.0, 1.0, 1.0, 0.0, 0.0],
    ]
