# tests/test_browser.py
"""The in-browser session (qminesweeper.browser), exercised on the server with
PurePyBackend — no Pyodide needed here; Pyodide loading is verified separately."""

from __future__ import annotations

import numpy as np
import pytest

from qminesweeper.browser import BrowserSession

_STATE_KEYS = {
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


def test_setup_returns_state_contract():
    s = BrowserSession()
    st = s.setup(4, 4, 0, 0, "sandbox", "one")
    assert set(st) == _STATE_KEYS
    assert st["status"] == "ONGOING"
    assert st["rows"] == 4 and st["cols"] == 4
    assert st["moveset"] == "ONE_QUBIT"
    assert st["grid"] == [[-1.0] * 4 for _ in range(4)]  # all unexplored


def test_move_then_reset():
    np.random.seed(0)
    s = BrowserSession()
    s.setup(3, 3, 0, 0, "sandbox", "one")  # 0 mines -> measuring is always safe
    after = s.move("1,1")
    assert after["status"] == "ONGOING"
    assert any(v != -1.0 for row in after["grid"] for v in row)  # something got explored
    reset = s.reset()
    assert reset["grid"] == [[-1.0] * 3 for _ in range(3)]  # back to all unexplored


def test_new_same_restarts_same_rules():
    s = BrowserSession()
    s.setup(2, 2, 0, 0, "sandbox", "one")
    s.move("1,1")
    st = s.new_same()
    assert st["status"] == "ONGOING"
    assert st["moveset"] == "ONE_QUBIT"


def test_two_qubit_gate_move_applies():
    s = BrowserSession()
    s.setup(2, 2, 0, 0, "sandbox", "two_extended")
    st = s.move("CX 1,1 2,2")  # must not raise
    assert st["status"] == "ONGOING"


def test_illegal_move_is_noop():
    s = BrowserSession()
    s.setup(2, 2, 0, 0, "sandbox", "one")
    before = s.state()
    after = s.move("CX 1,1 2,2")  # 2-qubit gate not in ONE_QUBIT moveset -> ignored
    assert after["grid"] == before["grid"]


def test_entangled_setup_runs():
    np.random.seed(1)
    s = BrowserSession()
    st = s.setup(3, 3, 2, 2, "clear", "two")  # PurePy random-Clifford mine sampling
    assert st["status"] == "ONGOING"


def test_state_before_setup_raises():
    with pytest.raises(RuntimeError):
        BrowserSession().state()


def test_export_import_save_restores_current_board():
    np.random.seed(2)
    original = BrowserSession()
    original.setup(3, 3, 0, 0, "sandbox", "two")
    moved = original.move("1,1")
    original.move("H 1,2")
    snapshot = original.export_save()

    restored = BrowserSession()
    state = restored.import_save(snapshot)

    assert snapshot["version"] == 1
    assert state["grid"] == original.state()["grid"]
    assert state["status"] == moved["status"]
    assert state["moveset"] == "TWO_QUBIT"
    assert restored.export_save() == snapshot


def test_import_save_rejects_unknown_version():
    s = BrowserSession()

    with pytest.raises(ValueError):
        s.import_save({"version": 999})


def test_export_save_before_setup_raises():
    with pytest.raises(RuntimeError):
        BrowserSession().export_save()
