# tests/test_analytics_store.py
"""
Tests for the analytics store's public admin-read API.

Admin reads and CSV export go through locked `SQLiteStore` methods rather than
the private connection, so these cover both the read contract itself and the
behaviour under concurrent readers and writers.

(conftest.py sets QMS_ENABLE_AUTH=0 and a known QMS_ADMIN_PASS before import.)
"""

from __future__ import annotations

import asyncio
import csv
import io
import sqlite3
import threading
from types import SimpleNamespace

import pytest

from qminesweeper.database import SQLiteStore

# Declaration order of the `games` table; the CSV header must match it exactly.
EXPECTED_COLUMNS = [
    "game_id",
    "user_id",
    "created_at",
    "last_seen",
    "rows",
    "cols",
    "mines",
    "ent_level",
    "win_cond",
    "moveset",
    "prep_circuit",
    "status",
    "ended_at",
    "resets",
    "moves_measures",
    "moves_gates",
    "source",
    "app_version",
]


@pytest.fixture
def store(tmp_path) -> SQLiteStore:
    """A fresh, empty store backed by a throwaway database file."""
    return SQLiteStore(tmp_path / "qms.sqlite")


def _create(store: SQLiteStore, game_id: str, *, ts: str, user_id: str = "u1") -> None:
    """Insert one game with fixed board parameters, varying only what tests assert on."""
    store.game_created(
        game_id=game_id,
        user_id=user_id,
        ts=ts,
        rows=5,
        cols=5,
        mines=3,
        ent_level=1,
        win_cond="IDENTIFY",
        moveset="FULL",
        prep_circuit=[("H", [0])],
    )


# ---------- column contract ----------
def test_game_columns_match_table_declaration_order(store: SQLiteStore):
    assert store.game_columns() == EXPECTED_COLUMNS


# ---------- empty export ----------
def test_export_games_reports_columns_when_empty(store: SQLiteStore):
    columns, rows = store.export_games()

    assert columns == EXPECTED_COLUMNS
    assert rows == []


def test_recent_games_is_empty_without_games(store: SQLiteStore):
    assert store.recent_games() == []


def test_download_db_writes_header_only_for_empty_database(store: SQLiteStore, monkeypatch):
    """The CSV route must emit a usable header even with nothing to export."""
    from qminesweeper import server
    from qminesweeper.server import ADMIN_COOKIE, _admin_serializer, download_db

    monkeypatch.setattr(server, "STATS_DB", store)
    request = SimpleNamespace(cookies={ADMIN_COOKIE: _admin_serializer().dumps("ok")})

    body = _read_streaming_body(download_db(request))
    parsed = list(csv.reader(io.StringIO(body)))

    assert parsed == [EXPECTED_COLUMNS]


def test_download_db_exports_rows_in_column_order(store: SQLiteStore, monkeypatch):
    from qminesweeper import server
    from qminesweeper.server import ADMIN_COOKIE, _admin_serializer, download_db

    _create(store, "g1", ts="2026-01-01T00:00:00+00:00")
    monkeypatch.setattr(server, "STATS_DB", store)
    request = SimpleNamespace(cookies={ADMIN_COOKIE: _admin_serializer().dumps("ok")})

    parsed = list(csv.reader(io.StringIO(_read_streaming_body(download_db(request)))))

    assert parsed[0] == EXPECTED_COLUMNS
    assert len(parsed) == 2
    row = dict(zip(EXPECTED_COLUMNS, parsed[1]))
    assert row["game_id"] == "g1"
    assert row["status"] == "ONGOING"
    assert row["moves_gates"] == "0"


def _read_streaming_body(response) -> str:
    """Read either a plain or streaming response body."""

    if hasattr(response, "body"):
        body = response.body
        return body if isinstance(body, str) else body.decode("utf-8")

    async def collect() -> str:
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))
        return "".join(chunks)

    return asyncio.run(collect())


# ---------- ordering and limit ----------
def test_recent_games_returns_newest_first_and_honours_limit(store: SQLiteStore):
    for i in range(5):
        _create(store, f"g{i}", ts=f"2026-01-0{i + 1}T00:00:00+00:00")

    newest = store.recent_games(limit=3)

    assert [row["game_id"] for row in newest] == ["g4", "g3", "g2"]


def test_recent_games_returns_plain_dicts(store: SQLiteStore):
    """Callers must not depend on the connection's sqlite3.Row factory."""
    _create(store, "g1", ts="2026-01-01T00:00:00+00:00")

    (row,) = store.recent_games()

    assert type(row) is dict


def test_admin_settings_round_trip_as_an_atomic_snapshot(store: SQLiteStore):
    first = {"ENABLE_HELP": False, "RESET_POLICY": "never"}
    second = {"ENABLE_HELP": True, "ENABLE_ENTANGLEMENT_PROBES": False}

    assert store.save_app_settings(first)
    assert store.load_app_settings() == first
    assert store.save_app_settings(second)
    assert store.load_app_settings() == second


# ---------- concurrency ----------
def test_concurrent_reads_and_writes_stay_consistent(store: SQLiteStore):
    """
    Hammer the store from several writer and reader threads at once.

    Reads previously bypassed the lock, so this pins the invariants that the
    locked API is there to provide: writes are not lost, readers never observe
    a row shape that disagrees with the declared columns, and no call raises.
    """
    writers, per_writer, readers = 4, 20, 4
    errors: list[BaseException] = []
    observed_totals: list[int] = []
    stop = threading.Event()
    # Release every thread at once so reads and writes genuinely interleave.
    start = threading.Barrier(writers + readers)

    def write(worker: int) -> None:
        try:
            start.wait()
            for i in range(per_writer):
                game_id = f"w{worker}-g{i}"
                _create(store, game_id, ts="2026-01-01T00:00:00+00:00", user_id=f"u{worker}")
                store.increment_move(game_id=game_id, kind="gate")
                store.heartbeat(game_id=game_id, ts="2026-01-01T00:01:00+00:00")
        except BaseException as exc:  # noqa: BLE001 - surfaced via the assertion below
            errors.append(exc)

    def read() -> None:
        try:
            start.wait()
            while not stop.is_set():
                observed_totals.append(store.summary()["total_games"])
                columns, rows = store.export_games()
                assert all(len(row) == len(columns) for row in rows)
                assert all(set(row) == set(columns) for row in store.recent_games(limit=10))
                store.online_active()
        except BaseException as exc:  # noqa: BLE001 - surfaced via the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(w,)) for w in range(writers)]
    threads += [threading.Thread(target=read) for _ in range(readers)]
    for thread in threads:
        thread.start()
    for thread in threads[:writers]:
        thread.join(timeout=60)
    stop.set()
    for thread in threads[writers:]:
        thread.join(timeout=60)

    assert errors == []
    assert not any(thread.is_alive() for thread in threads)

    expected_total = writers * per_writer
    summary = store.summary()
    assert summary["total_games"] == expected_total
    assert summary["unique_users"] == writers
    # Every write landed: no increment was lost to a concurrent read.
    columns, rows = store.export_games()
    gates = columns.index("moves_gates")
    assert len(rows) == expected_total
    assert all(row[gates] == 1 for row in rows)
    # Readers only ever saw counts the writers had actually reached.
    assert observed_totals, "readers never sampled the store"
    assert max(observed_totals) <= expected_total


def test_summary_is_atomic_against_concurrent_status_writes(store: SQLiteStore):
    """
    `summary()` issues one SELECT per counter, so it is only self-consistent
    while it holds the store lock for all of them.

    Every game is terminal and writers only ever flip WIN <-> LOST, so the
    number of games is fixed and `wins + losses` must equal it in every
    snapshot. An unlocked read can observe a game as it moves between the two
    counters and report a total that is off by one.
    """
    total = 40
    for i in range(total):
        _create(store, f"g{i}", ts="2026-01-01T00:00:00+00:00")
        store.outcome(game_id=f"g{i}", ts="2026-01-01T00:00:00+00:00", status="WIN")

    errors: list[BaseException] = []
    torn: list[dict] = []
    stop = threading.Event()
    start = threading.Barrier(3)

    def flip(status_a: str, status_b: str) -> None:
        try:
            start.wait()
            i = 0
            while not stop.is_set():
                game_id = f"g{i % total}"
                store.outcome(game_id=game_id, ts="2026-01-01T00:02:00+00:00", status=status_a)
                store.outcome(game_id=game_id, ts="2026-01-01T00:03:00+00:00", status=status_b)
                i += 1
        except BaseException as exc:  # noqa: BLE001 - surfaced via the assertion below
            errors.append(exc)

    def sample() -> None:
        try:
            start.wait()
            for _ in range(400):
                snapshot = store.summary()
                if snapshot["wins"] + snapshot["losses"] != total:
                    torn.append(snapshot)
        except BaseException as exc:  # noqa: BLE001 - surfaced via the assertion below
            errors.append(exc)
        finally:
            stop.set()

    threads = [
        threading.Thread(target=flip, args=("LOST", "WIN")),
        threading.Thread(target=flip, args=("WIN", "LOST")),
        threading.Thread(target=sample),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    assert not any(thread.is_alive() for thread in threads)
    assert torn == [], f"summary() observed a torn snapshot: {torn[:3]}"
    assert store.summary()["total_games"] == total


def test_older_database_gains_the_added_columns(tmp_path):
    """A database file created before `source` and `app_version` still opens.

    The columns are appended in place and existing rows take the declared
    defaults: 'server', because every row predating browser reporting was
    observed by the server, and '' for the version, which says the row has no
    recorded version rather than attributing it to the migrating release.
    """
    path = tmp_path / "legacy.sqlite"
    legacy = sqlite3.connect(str(path))
    with legacy:
        legacy.execute(
            """
            CREATE TABLE games (
              game_id TEXT PRIMARY KEY, user_id TEXT, created_at TEXT NOT NULL,
              last_seen TEXT NOT NULL, rows INTEGER NOT NULL, cols INTEGER NOT NULL,
              mines INTEGER NOT NULL, ent_level INTEGER NOT NULL, win_cond TEXT NOT NULL,
              moveset TEXT NOT NULL, prep_circuit TEXT NOT NULL, status TEXT, ended_at TEXT,
              resets INTEGER NOT NULL DEFAULT 0, moves_measures INTEGER NOT NULL DEFAULT 0,
              moves_gates INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        legacy.execute(
            "INSERT INTO games VALUES ('old','u','2026-01-01T00:00:00','2026-01-01T00:00:00',"
            "4,4,2,1,'CLEAR','CLASSIC','[]','WIN','2026-01-01T00:00:00',0,0,0)"
        )
    legacy.close()

    store = SQLiteStore(path)
    assert store.game_columns() == EXPECTED_COLUMNS
    row = store.recent_games(limit=1)[0]
    assert row["source"] == "server"
    assert row["app_version"] == ""
