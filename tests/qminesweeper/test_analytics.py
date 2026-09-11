# tests/qminesweeper/test_analytics.py
"""Browser analytics ingest: validation, storage invariants, and the route.

Routes are exercised by calling the handler with a stub request, matching the
style of test_server_logic.py; the repository has no HTTP test client.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from qminesweeper.auth import BasicAuthMiddleware
from qminesweeper.database import SQLiteStore
from qminesweeper.engine import MAX_DIM, MAX_ENT_LEVEL
from qminesweeper.server import (
    ANALYTICS_MAX_BODY_BYTES,
    ANALYTICS_MAX_GAMES,
    AUTH_EXEMPT_PATHS,
    _validate_analytics_game,
    analytics_ingest,
)


def _game(**overrides) -> dict:
    """A well-formed browser report, before any overrides."""
    row = {
        "game_id": "abc-123",
        "user_id": "user-1",
        "created_at": "2026-09-09T10:00:00",
        "last_seen": "2026-09-09T10:05:00",
        "ended_at": "2026-09-09T10:05:00",
        "rows": 5,
        "cols": 5,
        "mines": 4,
        "ent_level": 2,
        "win_cond": "identify",
        "moveset": "two_extended",
        "status": "WIN",
        "prep_circuit": [["H", [0]], ["CX", [0, 1]]],
        "resets": 1,
        "moves_measures": 7,
        "moves_gates": 3,
    }
    row.update(overrides)
    return row


class _StubRequest:
    """Minimal stand-in exposing the one method the handler awaits."""

    def __init__(self, body: bytes):
        self._body = body

    async def body(self) -> bytes:
        return self._body


def _post(payload, store, monkeypatch, *, enabled=True, raw: bytes | None = None):
    """Call the ingest handler against a temporary store."""
    from qminesweeper import server

    monkeypatch.setattr(server, "STATS_DB", store)
    monkeypatch.setattr(server.settings, "ENABLE_BROWSER_ANALYTICS", enabled)
    body = raw if raw is not None else json.dumps(payload).encode()
    return asyncio.run(analytics_ingest(_StubRequest(body)))


@pytest.fixture
def store(tmp_path) -> SQLiteStore:
    return SQLiteStore(tmp_path / "analytics.sqlite")


# ---------- defaults ----------
def test_collection_is_on_by_default():
    """Beta default: a deployment collects statistics however its players play.

    Pinned because these are the switches that decide whether any browser data
    is recorded at all, and a silent flip either way is easy to miss.
    """
    from qminesweeper.settings import Settings

    defaults = Settings(_env_file=None)
    assert defaults.ENABLE_BROWSER_ANALYTICS is True
    assert defaults.ENABLE_BROWSER_APP is True
    # Relative, so a build reports to whichever origin serves it and one bundle
    # works on any host.
    assert defaults.BROWSER_ANALYTICS_URL == "/analytics"
    # Same-origin only unless a deployment opts extra origins in.
    assert defaults.ANALYTICS_ALLOWED_ORIGINS == ""


# ---------- validation ----------
def test_valid_report_is_normalized():
    row = _validate_analytics_game(_game())
    assert row["game_id"] == "abc-123"
    assert row["moves_measures"] == 7
    assert row["prep_circuit"] == [["H", [0]], ["CX", [0, 1]]]


def test_optional_ended_at_may_be_absent():
    assert _validate_analytics_game(_game(ended_at=None, status="ONGOING"))["ended_at"] is None


def test_timestamps_are_ordered_and_not_future_dated():
    with pytest.raises(ValueError, match="created_at must not be after last_seen"):
        _validate_analytics_game(
            _game(created_at="2026-09-09T10:06:00Z", last_seen="2026-09-09T10:05:00Z")
        )
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with pytest.raises(ValueError, match="too far in the future"):
        _validate_analytics_game(_game(last_seen=future, ended_at=future))
    with pytest.raises(ValueError, match="ONGOING games must not have ended_at"):
        _validate_analytics_game(_game(status="ONGOING"))
    with pytest.raises(ValueError, match="finished games require ended_at"):
        _validate_analytics_game(_game(status="WIN", ended_at=None))


@pytest.mark.parametrize(
    "override",
    [
        {"game_id": ""},
        {"game_id": "has spaces"},
        {"game_id": "x" * 65},
        {"game_id": 42},
        {"user_id": "semi;colon"},
        {"rows": 0},
        {"rows": MAX_DIM + 1},
        {"cols": -1},
        {"mines": 26},  # exceeds rows * cols on a 5x5 board
        {"ent_level": MAX_ENT_LEVEL + 1},
        {"win_cond": "conquer"},
        {"moveset": "everything"},
        {"status": "PAUSED"},
        {"created_at": "not-a-date"},
        {"created_at": None},
        {"resets": -1},
        {"moves_gates": True},  # bool must not pass as int
        {"prep_circuit": "H"},
        {"prep_circuit": [["NOTAGATE", [0]]]},
        {"prep_circuit": [["H", [99]]]},  # target outside the board
        {"prep_circuit": [["H"]]},
        {"prep_circuit": [["H", []]]},
    ],
)
def test_malformed_reports_are_rejected(override):
    with pytest.raises(ValueError):
        _validate_analytics_game(_game(**override))


def test_non_object_report_is_rejected():
    with pytest.raises(ValueError):
        _validate_analytics_game(["not", "an", "object"])


# ---------- storage invariants ----------
def test_ingested_row_is_marked_as_browser(store):
    assert store.ingest_game(_validate_analytics_game(_game()))
    assert store.recent_games(limit=1)[0]["source"] == "browser"


def test_server_rows_are_marked_as_server(store):
    store.game_created(
        game_id="s1", user_id="u", ts="2026-09-09T10:00:00", rows=4, cols=4,
        mines=2, ent_level=1, win_cond="clear", moveset="classic", prep_circuit=[],
    )
    assert store.recent_games(limit=1)[0]["source"] == "server"


def test_browser_report_cannot_overwrite_a_server_game(store):
    """A client must not be able to rewrite real history by guessing a game_id."""
    store.game_created(
        game_id="s1", user_id="u", ts="2026-09-09T10:00:00", rows=4, cols=4,
        mines=2, ent_level=1, win_cond="clear", moveset="classic", prep_circuit=[],
    )
    assert store.ingest_game(_validate_analytics_game(_game(game_id="s1"))) is False
    row = next(r for r in store.recent_games(limit=5) if r["game_id"] == "s1")
    assert row["source"] == "server"
    assert row["moves_measures"] == 0


def test_reporting_the_same_game_twice_updates_in_place(store):
    """Offline clients resend, and an ongoing game is reported again when it ends."""
    store.ingest_game(_validate_analytics_game(_game(status="ONGOING", ended_at=None, moves_measures=2)))
    store.ingest_game(_validate_analytics_game(_game(status="WIN", moves_measures=9)))
    rows = store.recent_games(limit=10)
    assert len(rows) == 1
    assert rows[0]["status"] == "WIN"
    assert rows[0]["moves_measures"] == 9


def test_browser_rows_are_pruned_by_age_and_count(store):
    now = datetime.now(timezone.utc)
    for index in range(3):
        stamp = (now - timedelta(minutes=3 - index)).isoformat()
        store.ingest_game(
            _validate_analytics_game(
                _game(
                    game_id=f"new-{index}",
                    created_at=stamp,
                    last_seen=stamp,
                    ended_at=None,
                    status="ONGOING",
                )
            )
        )
    old = (now - timedelta(days=10)).isoformat()
    store.ingest_game(
        _validate_analytics_game(
            _game(game_id="old", created_at=old, last_seen=old, ended_at=None, status="ONGOING")
        )
    )

    assert store.prune_browser_analytics(max_rows=2, retention_days=5) == 2
    assert [row["game_id"] for row in store.recent_games(limit=10)] == ["new-2", "new-1"]


# ---------- route ----------
def test_route_is_hidden_when_ingest_is_disabled(store, monkeypatch):
    resp = _post({"games": [_game()]}, store, monkeypatch, enabled=False)
    assert resp.status_code == 404
    assert store.recent_games(limit=1) == []


def test_route_accepts_a_batch(store, monkeypatch):
    resp = _post({"games": [_game(game_id="g1"), _game(game_id="g2")]}, store, monkeypatch)
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert (body["accepted"], body["rejected"]) == (["g1", "g2"], 0)
    assert len(store.recent_games(limit=10)) == 2


def test_route_rate_limits_per_client_without_dropping_queue_data(store, monkeypatch):
    from qminesweeper import server

    server._analytics_global_requests.clear()
    server._analytics_client_requests.clear()
    monkeypatch.setattr(server.settings, "ANALYTICS_RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr(server.settings, "ANALYTICS_GLOBAL_LIMIT_PER_MINUTE", 10)

    assert _post({"games": [_game(game_id="first")]}, store, monkeypatch).status_code == 200
    limited = _post({"games": [_game(game_id="second")]}, store, monkeypatch)

    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
    assert [row["game_id"] for row in store.recent_games(limit=10)] == ["first"]


def test_runtime_browser_config_contains_all_game_product_settings(monkeypatch):
    from qminesweeper import server

    monkeypatch.setattr(server.settings, "RESET_POLICY", "never")
    monkeypatch.setattr(server.settings, "ENABLE_SURVEY", True)
    monkeypatch.setattr(server.settings, "SURVEY_URL", "https://example.test/survey")
    monkeypatch.setattr(server.settings, "ENABLE_ENTANGLEMENT_PROBES", False)

    body = json.loads(server.browser_app_config().body)

    assert body["product"]["entanglement_probes"] is False
    assert body["config"]["reset_policy"] == "never"
    assert body["config"]["enable_survey"] is True
    assert body["config"]["survey_url"] == "https://example.test/survey"
    assert body["config"]["entanglement_probes"] is False


def test_route_reports_the_online_count(store, monkeypatch):
    """The reply carries the active-game count so the app can show the counter.

    Riding on this response rather than a separate endpoint is what keeps the
    number honest: a client only learns it while itself reporting, so the count
    always includes players like it.
    """
    from qminesweeper import server

    monkeypatch.setattr(server, "_online_count", lambda: 4)
    resp = _post({"games": [_game()]}, store, monkeypatch)
    assert json.loads(resp.body)["online"] == 4


def test_route_keeps_valid_rows_from_a_partly_bad_batch(store, monkeypatch):
    """A client cannot repair a rejected row, so the good ones must still land."""
    resp = _post({"games": [_game(game_id="good"), _game(win_cond="conquer")]}, store, monkeypatch)
    body = json.loads(resp.body)
    assert (body["accepted"], body["rejected"]) == (["good"], 1)
    assert [r["game_id"] for r in store.recent_games(limit=10)] == ["good"]


@pytest.mark.parametrize(
    "payload,status",
    [
        ({"games": "nope"}, 400),
        ({}, 400),
        ({"games": [{} for _ in range(ANALYTICS_MAX_GAMES + 1)]}, 413),
    ],
)
def test_route_rejects_malformed_envelopes(store, monkeypatch, payload, status):
    assert _post(payload, store, monkeypatch).status_code == status


def test_route_rejects_non_json_and_oversized_bodies(store, monkeypatch):
    assert _post(None, store, monkeypatch, raw=b"{not json").status_code == 400
    assert _post(None, store, monkeypatch, raw=b"[]").status_code == 400
    assert _post(None, store, monkeypatch, raw=b"x" * (ANALYTICS_MAX_BODY_BYTES + 1)).status_code == 413


# ---------- installable PWA ----------
def test_pwa_paths_are_exempt_from_basic_auth():
    """The installable app must be reachable without the site password.

    A service worker cannot answer a Basic Auth challenge, so an installed app
    behind auth fails its update fetches. Both the bare path and the prefix are
    checked: without the bare one, the mount's redirect to /app/ is never
    reached and typing the address gets a password prompt.
    """
    middleware = BasicAuthMiddleware(app=None, username="u", password="p", exclude_paths=AUTH_EXEMPT_PATHS)
    for path in ("/app", "/app/", "/app/index.html", "/app/sw.js", "/app/py/chppy/tableau.py"):
        assert middleware._is_excluded(path), path
    # The server-rendered game and the admin pages stay protected.
    for path in ("/game", "/setup", "/admin", "/admin/db_download"):
        assert not middleware._is_excluded(path), path


def test_pwa_is_not_served_without_a_configured_bundle():
    """A deployment that does not distribute the app must not mount anything."""
    from qminesweeper import server

    if server.settings.BROWSER_DIST_DIR:
        pytest.skip("this environment configures a bundle directory")
    assert server.BROWSER_APP_AVAILABLE is False
    assert not any(getattr(route, "name", None) == "browser_app" for route in server.app.routes)


def test_browser_app_flag_gates_the_routes(monkeypatch):
    """QMS_ENABLE_BROWSER_APP is enforced per request, not only at startup.

    The mount is created once, but the setting is live (the admin dashboard can
    change it), so turning it off must hide /app immediately.
    """
    from qminesweeper import server

    async def served(_request):
        return "served"

    def ask(path: str):
        request = SimpleNamespace(url=SimpleNamespace(path=path))
        return asyncio.run(server.gate_browser_app(request, served))

    monkeypatch.setattr(server.settings, "ENABLE_BROWSER_APP", False)
    for path in ("/app", "/app/", "/app/index.html"):
        assert getattr(ask(path), "status_code", None) == 404, path
    # Everything else is untouched by the gate.
    assert ask("/setup") == "served"
    assert ask("/application-form") == "served"  # not a /app/ path despite the prefix

    monkeypatch.setattr(server.settings, "ENABLE_BROWSER_APP", True)
    assert ask("/app/") == "served"


def test_features_offer_the_app_only_when_a_bundle_exists():
    """The switch cannot conjure a bundle, so both must be true to offer it."""
    from qminesweeper.settings import Settings

    product = Settings(_env_file=None, ENABLE_BROWSER_APP=True).product_config()
    assert product.template_features(browser_app_available=True)["ENABLE_BROWSER_APP"] is True
    assert product.template_features(browser_app_available=False)["ENABLE_BROWSER_APP"] is False
    # The browser build is itself the app and must not link to one.
    assert product.template_features(browser_app_available=False)["ENABLE_BROWSER_APP"] is False


# ---------- auth exemption ----------
def test_ingest_path_is_exempt_from_basic_auth():
    """A browser-only client has no site credentials, so the route must be open.

    Uses the list server.py actually passes to enable_basic_auth, so removing
    the exemption fails here. The suite runs with auth disabled, so the
    middleware is constructed directly.
    """
    middleware = BasicAuthMiddleware(app=None, username="u", password="p", exclude_paths=AUTH_EXEMPT_PATHS)
    assert middleware._is_excluded("/analytics")
    assert middleware._is_excluded("/app/config")
    assert not middleware._is_excluded("/game")


# ---------- browser session records ----------
def _session():
    import numpy as np

    from qminesweeper.browser import BrowserSession

    np.random.seed(11)
    session = BrowserSession()
    session.setup(rows=4, cols=4, mines=2, ent_level=1, win="identify", moves="two_extended")
    return session


def test_session_has_no_record_before_a_game():
    from qminesweeper.browser import BrowserSession

    assert BrowserSession().analytics_record() is None


def test_session_record_starts_a_new_game():
    record = _session().analytics_record()
    assert record["status"] == "ONGOING"
    assert record["ended_at"] is None
    assert (record["resets"], record["moves_measures"], record["moves_gates"]) == (0, 0, 0)
    assert record["win_cond"] == "identify" and record["moveset"] == "two_extended"


def test_each_game_gets_its_own_id():
    session = _session()
    first = session.analytics_record()["game_id"]
    session.new_same()
    assert session.analytics_record()["game_id"] != first


def test_counters_match_the_server_rules():
    """Gates and measures count; pins and rejected commands do not."""
    session = _session()
    session.move("X 1,1")
    session.move("2,2")
    session.move("P 3,3")  # pins are never counted
    session.move("9,9")  # out of bounds: a silent no-op
    record = session.analytics_record()
    assert (record["moves_gates"], record["moves_measures"]) == (1, 1)


def test_reset_zeroes_counters_and_counts_the_reset():
    session = _session()
    session.move("X 1,1")
    session.reset()
    record = session.analytics_record()
    assert (record["resets"], record["moves_gates"], record["moves_measures"]) == (1, 0, 0)
    assert record["status"] == "ONGOING" and record["ended_at"] is None


def test_record_is_a_copy():
    """A caller holding a record must not see it change as play continues."""
    session = _session()
    held = session.analytics_record()
    session.move("X 1,1")
    assert held["moves_gates"] == 0


def test_record_survives_save_and_restore():
    from qminesweeper.browser import BrowserSession

    session = _session()
    session.move("X 1,1")
    snapshot = session.export_save()
    before = session.analytics_record()

    restored = BrowserSession()
    restored.import_save(snapshot)
    after = restored.analytics_record()
    # Same id and counters, so reporting again updates one row instead of two.
    assert after["game_id"] == before["game_id"]
    assert after["moves_gates"] == before["moves_gates"]
    restored.move("X 2,2")
    assert restored.analytics_record()["moves_gates"] == before["moves_gates"] + 1


def test_save_without_analytics_still_restores():
    """Saves written before analytics existed must not break, and must not lie."""
    from qminesweeper.browser import BrowserSession

    snapshot = _session().export_save()
    snapshot.pop("analytics")
    restored = BrowserSession()
    restored.import_save(snapshot)
    assert restored.analytics_record() is None


def test_a_real_session_record_passes_server_validation():
    """The two halves must agree: what the browser produces, the server accepts."""
    session = _session()
    session.move("X 1,1")
    session.move("2,2")
    row = _validate_analytics_game(session.analytics_record())
    assert row["game_id"] == session.analytics_record()["game_id"]
