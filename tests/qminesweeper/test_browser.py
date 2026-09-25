# tests/test_browser.py
"""The in-browser session (qminesweeper.browser), exercised on the server with
ChppyBackend — no Pyodide needed here; Pyodide loading is verified separately."""

from __future__ import annotations

import json

import numpy as np
import pytest

from qminesweeper.browser import SAVE_VERSION, BrowserSession

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


def test_two_qubit_gate_on_one_cell_is_noop():
    s = BrowserSession()
    s.setup(2, 2, 0, 0, "sandbox", "two_extended")
    s.move("H 1,1")
    before = s.export_save()
    after = s.move("CX 1,1 1,1")
    assert after["grid"] == s.state()["grid"]
    assert s.export_save()["tableau"] == before["tableau"]
    assert s._board.state.is_valid()


def _version_1_save(session: BrowserSession) -> dict:
    """The snapshot as version 1 wrote it: the tableau as nested 0/1 lists."""
    snapshot = session.export_save()
    state = session._board.state
    snapshot["version"] = 1
    snapshot["tableau"] = {"n": state.n, "x": state.x.tolist(), "z": state.z.tolist(), "r": state.r.tolist()}
    return snapshot


def test_version_1_saves_still_restore():
    np.random.seed(4)
    original = BrowserSession()
    original.setup(4, 4, 3, 2, "clear", "two")
    original.move("H 2,2")
    restored = BrowserSession()
    assert restored.import_save(_version_1_save(original)) == original.state()
    assert restored.export_save()["tableau"] == original.export_save()["tableau"]


def test_save_is_compact_on_the_largest_preset():
    """Written after every move, so it must not carry the tableau as JSON lists."""
    np.random.seed(5)
    session = BrowserSession()
    session.setup(25, 15, 60, 2, "clear", "two")
    packed = len(json.dumps(session.export_save()))
    as_lists = len(json.dumps(_version_1_save(session)))
    assert packed < 150_000
    assert packed * 10 < as_lists


def test_import_save_rejects_a_corrupted_tableau():
    """A save from before same-cell gates were refused may hold broken state."""
    np.random.seed(3)
    original = BrowserSession()
    original.setup(3, 3, 2, 2, "clear", "two")
    snapshot = _version_1_save(original)
    for row in snapshot["tableau"]["x"]:
        row[4] = 0
    for row in snapshot["tableau"]["z"]:
        row[4] = 0

    with pytest.raises(ValueError, match="malformed browser save"):
        BrowserSession().import_save(snapshot)


@pytest.mark.parametrize("bits", ["", "AAAA", "not base64!"])
def test_import_save_rejects_packed_bits_that_do_not_fit(bits: str):
    s = BrowserSession()
    s.setup(3, 3, 0, 0, "sandbox", "two")
    snapshot = s.export_save()
    snapshot["tableau"]["x"] = bits

    with pytest.raises(ValueError, match="malformed browser save"):
        BrowserSession().import_save(snapshot)


def test_illegal_move_is_noop():
    s = BrowserSession()
    s.setup(2, 2, 0, 0, "sandbox", "one")
    before = s.state()
    after = s.move("CX 1,1 2,2")  # 2-qubit gate not in ONE_QUBIT moveset -> ignored
    assert after["grid"] == before["grid"]


def test_entangled_setup_runs():
    np.random.seed(1)
    s = BrowserSession()
    st = s.setup(3, 3, 2, 2, "clear", "two")  # chppy random-Clifford mine sampling
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

    assert snapshot["version"] == SAVE_VERSION == 2
    assert state["grid"] == original.state()["grid"]
    assert state["status"] == moved["status"]
    assert state["moveset"] == "TWO_QUBIT"
    assert restored.export_save() == snapshot


def test_import_save_rejects_unknown_version():
    s = BrowserSession()

    with pytest.raises(ValueError):
        s.import_save({"version": 999})


def test_import_save_rejects_missing_keys():
    s = BrowserSession()

    with pytest.raises(ValueError, match="malformed browser save"):
        s.import_save({"version": 1})


def test_export_save_before_setup_raises():
    with pytest.raises(RuntimeError):
        BrowserSession().export_save()
