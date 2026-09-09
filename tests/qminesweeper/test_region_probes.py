"""Runtime contract for the optional region entropy diagnostics."""

from __future__ import annotations

import asyncio
import copy
import json

import pytest

from qminesweeper import server
from qminesweeper.browser import BrowserSession
from qminesweeper.engine import validate_setup_params


def test_probe_validation_and_disabled_rules_are_strict():
    session = BrowserSession()
    session.setup(2, 2, 0, 0, "sandbox", "two_extended", True, True)
    for area in ([], [True], [0.0], [0, 0], [-1], [4], (0,)):
        with pytest.raises(ValueError):
            session.probe(area)  # type: ignore[arg-type]
    for area in ([], [True], [0.0], [1, 1], [-1], [4], (1,)):
        with pytest.raises(ValueError):
            session.probe([0], area)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="overlap"):
        session.probe([0], [0])
    disabled_two_area = BrowserSession()
    disabled_two_area.setup(2, 2, 0, 0, "sandbox", "two_extended", True, False)
    with pytest.raises(ValueError, match="disabled"):
        disabled_two_area.probe([0], [1])
    disabled = BrowserSession()
    disabled.setup(2, 2, 0, 0, "sandbox", "two_extended", False, True)
    with pytest.raises(ValueError, match="disabled"):
        disabled.probe([0])

    with pytest.raises(ValueError, match="boolean"):
        validate_setup_params(2, 2, 0, 0, entanglement_probes=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="boolean"):
        validate_setup_params(2, 2, 0, 0, two_area_probes=0)  # type: ignore[arg-type]


def test_two_area_probe_returns_mutual_information_without_mutation():
    session = BrowserSession()
    session.setup(2, 2, 0, 0, "sandbox", "two_extended", True, True)
    session.move("H 1,1")
    session.move("CX 1,1 1,2")
    before = copy.deepcopy(session.export_save())
    result = session.probe([0], [1])
    assert result["entropy_a"] == pytest.approx(1.0)
    assert result["entropy_b"] == pytest.approx(1.0)
    assert result["entropy_union"] == pytest.approx(0.0)
    assert result["mutual_information"] == pytest.approx(2.0)
    assert session.export_save() == before


def test_ghz_probe_mutual_information_is_one_bit():
    session = BrowserSession()
    session.setup(1, 3, 0, 0, "sandbox", "two_extended", True, True)
    session.move("H 1,1")
    session.move("CX 1,1 1,2")
    session.move("CX 1,1 1,3")
    result = session.probe([0], [1])
    assert result["mutual_information"] == pytest.approx(1.0)


def test_probe_flags_survive_new_same_and_save_migration():
    session = BrowserSession()
    session.setup(2, 2, 0, 0, "sandbox", "one", False, False)
    assert session.config() == {"entanglement_probes": False, "two_area_probes": False}
    session.new_same()
    assert session.config() == {"entanglement_probes": False, "two_area_probes": False}

    old_save = session.export_save()
    old_save["params"].pop("entanglement_probes")
    old_save["params"].pop("two_area_probes")
    restored = BrowserSession()
    restored.import_save(old_save)
    assert restored.config() == {"entanglement_probes": True, "two_area_probes": False}


def test_import_save_rejects_non_boolean_probe_flags():
    session = BrowserSession()
    session.setup(2, 2, 0, 0, "sandbox", "one")
    save = session.export_save()
    save["params"]["entanglement_probes"] = 1
    with pytest.raises(ValueError, match="malformed browser save"):
        session.import_save(save)
    assert session.config() == {"entanglement_probes": True, "two_area_probes": False}


def test_failed_setup_preserves_previous_rule_flags():
    session = BrowserSession()
    session.setup(2, 2, 0, 0, "sandbox", "one", False, False)
    with pytest.raises(ValueError):
        session.setup(0, 2, 0, 0, "sandbox", "one", True, True)
    assert session.config() == {"entanglement_probes": False, "two_area_probes": False}


def _json_request(payload: object):
    from starlette.requests import Request

    body = json.dumps(payload).encode()
    consumed = False

    async def receive():
        nonlocal consumed
        if consumed:
            return {"type": "http.disconnect"}
        consumed = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/probe",
            "headers": [(b"content-type", b"application/json")],
        },
        receive,
    )


async def _server_probe_success_errors_expiry_and_no_analytics():
    gid = "probe-test"
    board, game = server.build_board_and_game(
        2, 2, 0, 0, server.WinCondition.SANDBOX, server.MoveSet.TWO_QUBIT_EXTENDED, True, True
    )
    server.GAMES[gid] = {"board": board, "game": game, "config": {}, "last_seen": None}
    before = copy.deepcopy(board.export_numeric_grid().tolist())
    try:
        response = await server.probe_post(_json_request({"area_a": [0], "area_b": [1]}), gid)
        assert response.status_code == 200
        assert set(json.loads(response.body)) == {"entropy_a", "entropy_b", "entropy_union", "mutual_information"}
        assert board.export_numeric_grid().tolist() == before

        bad = await server.probe_post(_json_request({"area_a": [0], "area_b": [0]}), gid)
        assert bad.status_code == 400
        disabled_board, disabled_game = server.build_board_and_game(
            2, 2, 0, 0, server.WinCondition.SANDBOX, server.MoveSet.TWO_QUBIT_EXTENDED, False, True
        )
        server.GAMES["disabled"] = {"board": disabled_board, "game": disabled_game, "config": {}, "last_seen": None}
        disabled = await server.probe_post(_json_request({"area_a": [0]}), "disabled")
        assert disabled.status_code == 400
        expired = await server.probe_post(_json_request({"area_a": [0]}), "missing")
        assert expired.status_code == 404
        assert json.loads(expired.body) == {"error": "game_not_found", "redirect": "/setup"}
    finally:
        server.GAMES.pop(gid, None)
        server.GAMES.pop("disabled", None)


def test_server_probe_success_errors_expiry_and_no_analytics():
    asyncio.run(_server_probe_success_errors_expiry_and_no_analytics())


def test_probe_rules_follow_the_requested_region_count():
    from qminesweeper.engine import PROBE_REGION_LIMIT, probe_rules_for_regions

    assert probe_rules_for_regions(0, PROBE_REGION_LIMIT) == (False, False)
    assert probe_rules_for_regions(1, PROBE_REGION_LIMIT) == (True, False)
    assert probe_rules_for_regions(2, PROBE_REGION_LIMIT) == (True, True)
    # Never more than the game implements, or than the deployment allows.
    assert probe_rules_for_regions(PROBE_REGION_LIMIT + 3, PROBE_REGION_LIMIT) == (True, True)
    assert probe_rules_for_regions(2, 1) == (True, False)
    assert probe_rules_for_regions(2, 0) == (False, False)
    assert probe_rules_for_regions(-1, PROBE_REGION_LIMIT) == (False, False)


def test_probe_rules_narrow_stored_flags_to_a_region_limit():
    """The boolean form, used when rebuilding a game from its stored rules."""
    from qminesweeper.engine import PROBE_REGION_LIMIT, probe_rules_for_limit

    assert probe_rules_for_limit(True, True, PROBE_REGION_LIMIT) == (True, True)
    assert probe_rules_for_limit(True, True, 1) == (True, False)
    assert probe_rules_for_limit(True, True, 0) == (False, False)
    # A ceiling, never a switch that turns a rule back on.
    assert probe_rules_for_limit(False, False, PROBE_REGION_LIMIT) == (False, False)
    assert probe_rules_for_limit(False, True, PROBE_REGION_LIMIT) == (False, False)


def test_setup_tiers_reach_templates():
    from qminesweeper.engine import PROBE_REGION_DEFAULT, PROBE_REGION_LIMIT
    from qminesweeper.view_context import build_features

    features = build_features()
    # The deployment switch is a boolean; the region counts are game tiers the
    # setup form renders as choices.
    assert features["ENABLE_ENTANGLEMENT_PROBES"] is True
    assert features["PROBE_REGION_LIMIT"] == PROBE_REGION_LIMIT
    assert features["PROBE_REGION_DEFAULT"] == PROBE_REGION_DEFAULT
    assert PROBE_REGION_DEFAULT <= PROBE_REGION_LIMIT
    assert build_features(enable_entanglement_probes=False)["ENABLE_ENTANGLEMENT_PROBES"] is False


def test_settings_enable_probes_by_default():
    from qminesweeper.settings import Settings

    assert Settings(_env_file=None).ENABLE_ENTANGLEMENT_PROBES is True


@pytest.mark.parametrize(
    ("enabled", "requested", "expected"),
    [
        (True, 0, (False, False)),
        (True, 1, (True, False)),
        (True, 2, (True, True)),
        (False, 2, (False, False)),  # switched off: setup cannot ask its way back in
    ],
)
def test_server_probe_rules_respect_the_deployment_switch(monkeypatch, enabled, requested, expected):
    from qminesweeper.engine import probe_rules_for_regions

    monkeypatch.setattr(server.settings, "ENABLE_ENTANGLEMENT_PROBES", enabled)
    probes, two_area = probe_rules_for_regions(requested, server._probe_region_limit())
    _, game = server.build_board_and_game(
        2, 2, 0, 0, server.WinCondition.SANDBOX, server.MoveSet.TWO_QUBIT_EXTENDED, probes, two_area
    )
    assert (game.cfg.entanglement_probes, game.cfg.two_area_probes) == expected


def test_disabled_deployment_strips_probes_from_an_existing_game(monkeypatch):
    """new-same rebuilds through the same clamp, so a flag flip takes effect."""
    monkeypatch.setattr(server.settings, "ENABLE_ENTANGLEMENT_PROBES", False)
    _, game = server.build_board_and_game(
        2, 2, 0, 0, server.WinCondition.SANDBOX, server.MoveSet.TWO_QUBIT_EXTENDED, True, True
    )
    assert (game.cfg.entanglement_probes, game.cfg.two_area_probes) == (False, False)
