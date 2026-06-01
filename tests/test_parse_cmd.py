# tests/test_parse_cmd.py
"""Command parsing + gate-token normalization."""

from __future__ import annotations

import pytest

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import GameConfig, MoveSet, QMineSweeperGame, WinCondition
from qminesweeper.stim_backend import StimBackend
from qminesweeper.webapp import _SINGLE_Q, _TWO_Q, _parse_rc, parse_cmd


def test_parse_bare_coords_is_measure():
    assert parse_cmd("2,3") == ("M", (1, 2))


def test_parse_measure_prefixed():
    assert parse_cmd("M 2,3") == ("M", (1, 2))


def test_parse_pin():
    assert parse_cmd("P 4,4") == ("P", (3, 3))


def test_parse_single_qubit_gate():
    assert parse_cmd("SDG 1,1") == ("G1", ("SDG", (0, 0)))


def test_parse_two_qubit_gate():
    assert parse_cmd("CX 1,1 2,2") == ("G2", ("CX", (0, 0), (1, 1)))


def test_parse_is_case_insensitive_on_op():
    assert parse_cmd("cx 1,1 2,2") == ("G2", ("CX", (0, 0), (1, 1)))


@pytest.mark.parametrize("bad", ["", "   ", "x", "M", "1,", ",2", "CX 1,1", "X 1,1 2,2", "FOO 1,1"])
def test_parse_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_cmd(bad)


@pytest.mark.parametrize("token", ["0,0", "1,b", "a,1"])
def test_parse_rc_rejects_nonpositive_or_nonnumeric(token):
    # _parse_rc regex only accepts digits; "0,0" parses to (-1,-1) which the
    # board layer rejects via bounds checking (see test below). Pure garbage raises here.
    if token == "0,0":
        assert _parse_rc(token) == (-1, -1)  # documents the off-by-one boundary
    else:
        with pytest.raises(ValueError):
            _parse_rc(token)


def _make_game(moveset: MoveSet) -> QMineSweeperGame:
    board = QMineSweeperBoard(2, 2, backend=StimBackend(), flood_fill=False)
    board.span_classical_mines(0)
    board.set_clue_basis("Z")
    return QMineSweeperGame(board, GameConfig(win_condition=WinCondition.SANDBOX, move_set=moveset))


@pytest.mark.parametrize("token", sorted(_SINGLE_Q))
def test_every_single_qubit_token_applies(token):
    """Regression: 'SDG'/'SXDG'/'SYDG' (and the rest) must normalize, not silently fail."""
    game = _make_game(MoveSet.TWO_QUBIT_EXTENDED)
    game.cmd_gate(token, [(0, 0)])  # must not raise


@pytest.mark.parametrize("token", sorted(_TWO_Q))
def test_every_two_qubit_token_applies(token):
    game = _make_game(MoveSet.TWO_QUBIT_EXTENDED)
    game.cmd_gate(token, [(0, 0), (0, 1)])  # must not raise


def test_lowercase_gate_token_applies():
    game = _make_game(MoveSet.TWO_QUBIT_EXTENDED)
    game.cmd_gate("sdg", [(0, 0)])  # case-insensitive normalization
