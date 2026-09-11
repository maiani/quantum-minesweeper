# qminesweeper/database.py
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("qminesweeper.web")


def _is_writable_dir(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".qms_write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def default_db_path() -> Path:
    """
    Choose a sensible DB location:

    1) QMS_DB_PATH if set.
    2) /data/qms.sqlite if /data is writable (Cloud Run / Docker default).
    3) ~/.local/share/qminesweeper/qms.sqlite (XDG-style fallback).
    4) ./qms_data/qms.sqlite (last resort).
    """

    # 1) explicit env
    env = os.getenv("QMS_DB_PATH")
    if env:
        p = Path(env).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # 2) container-friendly /data
    data_dir = Path("/data")
    if _is_writable_dir(data_dir):
        return data_dir / "qms.sqlite"

    # 3) XDG-style local dir
    local_dir = Path.home() / ".local" / "share" / "qminesweeper"
    if _is_writable_dir(local_dir):
        return local_dir / "qms.sqlite"

    # 4) project-local folder
    proj_data = Path.cwd() / "qms_data"
    proj_data.mkdir(parents=True, exist_ok=True)
    return proj_data / "qms.sqlite"

# ---------- Store ----------


class SQLiteStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False => we guard with a lock
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init()

    def _init(self):
        with self._db:
            self._db.execute("PRAGMA journal_mode=WAL;")
            self._db.execute("PRAGMA synchronous=NORMAL;")
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS games (
                  game_id      TEXT PRIMARY KEY,
                  user_id      TEXT,
                  created_at   TEXT NOT NULL,
                  last_seen    TEXT NOT NULL,
                  rows         INTEGER NOT NULL,
                  cols         INTEGER NOT NULL,
                  mines        INTEGER NOT NULL,
                  ent_level    INTEGER NOT NULL,
                  win_cond     TEXT NOT NULL,
                  moveset      TEXT NOT NULL,
                  prep_circuit TEXT NOT NULL,   -- JSON [(gate,[targets]),...]
                  status       TEXT,            -- ONGOING/WIN/LOST/ABANDONED
                  ended_at     TEXT,
                  resets       INTEGER NOT NULL DEFAULT 0,
                  moves_measures   INTEGER NOT NULL DEFAULT 0,
                  moves_gates      INTEGER NOT NULL DEFAULT 0,
                  source       TEXT NOT NULL DEFAULT 'server',
                  app_version  TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_games_user ON games(user_id)")
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_games_last_seen ON games(last_seen)")
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                  key   TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                )
                """
            )
            self._migrate_add_columns()

    # Columns added to `games` after the table first shipped, with the DDL that
    # appends them to an existing database. Each default is chosen so that rows
    # written before the column existed keep a truthful value:
    #
    #   source       Rows written by the server are authoritative because the
    #                server ran the game; rows reported by a browser-only
    #                session are client-asserted. They share this table so the
    #                dashboard and CSV export keep working unchanged, and this
    #                column is what lets any analysis separate the two. Existing
    #                rows predate browser reporting, so 'server' is correct.
    #   app_version  Which release produced the row, so a behaviour change can
    #                be read against the version it shipped in. Older rows have
    #                no recorded version, and '' says exactly that rather than
    #                attributing them to whichever release did the migration.
    #
    # Keep this list in the same order as the CREATE TABLE above, so a migrated
    # database and a freshly created one agree on column order and the CSV
    # export has one stable header.
    _ADDED_COLUMNS: tuple[tuple[str, str], ...] = (
        ("source", "TEXT NOT NULL DEFAULT 'server'"),
        ("app_version", "TEXT NOT NULL DEFAULT ''"),
    )

    def _migrate_add_columns(self) -> None:
        """Append any `games` columns missing from an older database file."""
        cur = self._db.execute("PRAGMA table_info(games)")
        existing = {str(row["name"]) for row in cur.fetchall()}
        for name, ddl in self._ADDED_COLUMNS:
            if name in existing:
                continue
            try:
                self._db.execute(f"ALTER TABLE games ADD COLUMN {name} {ddl}")
                log.info(f"Migrated games table: added {name} column")
            except sqlite3.Error as e:
                # Never let analytics break startup. Unlike CREATE TABLE IF NOT
                # EXISTS, an ALTER always writes, so a read-only database file
                # would otherwise take the whole server down on a schema it
                # could previously open. Such a database cannot accept any write
                # anyway, so the game keeps running and every write logs its own
                # failure.
                log.error(f"Could not add games.{name} column, analytics writes will fail: {e}")

    def normalize_column_values(self, column: str, mapping: Dict[str, str]) -> int:
        """Rewrite legacy spellings in one `games` column. Returns rows changed.

        Purely mechanical: the caller owns the vocabulary and passes the old
        value -> new value map, so this module keeps knowing nothing about game
        rules. `column` is interpolated into the statement because SQLite cannot
        bind an identifier, so it is checked against the real table definition
        first and an unknown name is refused rather than executed.

        Runs on every startup and is idempotent: once a value has been rewritten
        it no longer matches any key, so later runs update nothing.
        """
        if column not in self.game_columns():
            log.error(f"Refusing to normalize unknown games column {column!r}")
            return 0
        changes = {old: new for old, new in mapping.items() if old != new}
        if not changes:
            return 0
        try:
            with self._lock, self._db:
                total = 0
                for old, new in changes.items():
                    # The identifier is interpolated, the values are bound;
                    # `column` was checked against the table above.
                    cur = self._db.execute(
                        f"UPDATE games SET {column}=? WHERE {column}=?",
                        (new, old),
                    )
                    total += cur.rowcount
            if total:
                log.info(f"Normalized {total} legacy games.{column} value(s)")
            return total
        except Exception as e:
            log.exception(f"DB normalize_column_values failed column={column}: {e}")
            return 0

    # --- lifecycle ---
    def game_created(
        self,
        *,
        game_id: str,
        user_id: Optional[str],
        ts: str,
        rows: int,
        cols: int,
        mines: int,
        ent_level: int,
        win_cond: str,
        moveset: str,
        prep_circuit: list[tuple[str, list[int]]],
        source: str = "server",
        app_version: str = "",
    ):
        """Insert a new game row with explicit ONGOING status and zeroed counters."""
        try:
            with self._lock, self._db:
                self._db.execute(
                    """
                    INSERT OR REPLACE INTO games
                    (game_id,user_id,created_at,last_seen,rows,cols,mines,ent_level,win_cond,moveset,
                     prep_circuit,status,ended_at,resets,moves_measures,moves_gates,source,app_version)
                    VALUES
                    (?,?,?,?,?,?,?,?,?,?,?, 'ONGOING', NULL, 0, 0, 0, ?, ?)
                    """,
                    (
                        game_id,
                        user_id or "",
                        ts,
                        ts,
                        rows,
                        cols,
                        mines,
                        ent_level,
                        win_cond,
                        moveset,
                        json.dumps(prep_circuit),
                        source,
                        app_version,
                    ),
                )
        except Exception as e:
            log.exception(f"DB game_created failed gid={game_id}: {e}")

    def ingest_game(self, row: Dict[str, Any]) -> bool:
        """Upsert one browser-reported game row. Returns True if it was stored.

        A browser-only session has no server to record its progress, so it
        reports the whole row rather than incremental events. That makes the
        write idempotent, which matters because a client that was offline may
        flush the same report more than once, and a game reported while ongoing
        is later reported again when it ends.

        The row is client-asserted: anyone can post to the ingest endpoint. Two
        things follow. It is always stored with ``source='browser'`` so analysis
        can separate it from server-authoritative rows, and it will never
        overwrite a row the server wrote, so a client cannot rewrite real game
        history by guessing a ``game_id``. Field validation belongs to the
        endpoint; this method owns the storage invariants.
        """
        try:
            with self._lock, self._db:
                cur = self._db.execute("SELECT source FROM games WHERE game_id = ?", (row["game_id"],))
                existing = cur.fetchone()
                if existing is not None and str(existing["source"]) != "browser":
                    log.warning(f"Refused browser analytics for server-owned game {row['game_id']}")
                    return False
                self._db.execute(
                    """
                    INSERT OR REPLACE INTO games
                    (game_id,user_id,created_at,last_seen,rows,cols,mines,ent_level,win_cond,moveset,
                     prep_circuit,status,ended_at,resets,moves_measures,moves_gates,source,app_version)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'browser', ?)
                    """,
                    (
                        row["game_id"],
                        row.get("user_id") or "",
                        row["created_at"],
                        row["last_seen"],
                        row["rows"],
                        row["cols"],
                        row["mines"],
                        row["ent_level"],
                        row["win_cond"],
                        row["moveset"],
                        json.dumps(row.get("prep_circuit") or []),
                        row.get("status"),
                        row.get("ended_at"),
                        row.get("resets", 0),
                        row.get("moves_measures", 0),
                        row.get("moves_gates", 0),
                        row.get("app_version") or "",
                    ),
                )
            return True
        except Exception as e:
            log.exception(f"DB ingest_game failed gid={row.get('game_id')}: {e}")
            return False

    def prune_browser_analytics(self, *, max_rows: int, retention_days: int) -> int:
        """Bound client-asserted analytics by age and newest-row count."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cutoff_iso = cutoff.isoformat()
        try:
            with self._lock, self._db:
                old = self._db.execute(
                    "DELETE FROM games WHERE source='browser' AND last_seen < ?",
                    (cutoff_iso,),
                ).rowcount
                excess = self._db.execute(
                    """
                    DELETE FROM games
                    WHERE source='browser' AND game_id NOT IN (
                      SELECT game_id FROM games
                      WHERE source='browser'
                      ORDER BY last_seen DESC
                      LIMIT ?
                    )
                    """,
                    (max_rows,),
                ).rowcount
                return old + excess
        except Exception as e:
            log.exception(f"DB prune_browser_analytics failed: {e}")
            return 0

    def heartbeat(self, *, game_id: str, ts: str):
        """Update last_seen for a game (no-op on error)."""
        try:
            with self._lock, self._db:
                self._db.execute("UPDATE games SET last_seen=? WHERE game_id=?", (ts, game_id))
        except Exception as e:
            log.exception(f"DB heartbeat failed gid={game_id}: {e}")

    def outcome(self, *, game_id: str, ts: str, status: str):
        """Set terminal outcome (WIN/LOST/ABANDONED) and stamp ended_at/last_seen."""
        try:
            with self._lock, self._db:
                self._db.execute(
                    "UPDATE games SET status=?, ended_at=?, last_seen=? WHERE game_id=?",
                    (status, ts, ts, game_id),
                )
        except Exception as e:
            log.exception(f"DB outcome failed gid={game_id}, status={status}: {e}")

    def reset_move_counters(self, *, game_id: str, ts: Optional[str] = None):
        """
        Atomically:
          - increments resets
          - zeros moves_measures/moves_gates
          - sets status='ONGOING', ended_at=NULL
          - updates last_seen to ts (or now)
        """
        ts = ts or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        try:
            with self._lock, self._db:
                self._db.execute(
                    """
                    UPDATE games
                    SET resets = resets + 1,
                        moves_measures = 0,
                        moves_gates = 0,
                        status = 'ONGOING',
                        ended_at = NULL,
                        last_seen = ?
                    WHERE game_id=?
                    """,
                    (ts, game_id),
                )
        except Exception as e:
            log.exception(f"DB reset_move_counters failed gid={game_id}: {e}")

    def prune_abandoned(self, *, minutes: int) -> int:
        """
        Mark games older than `minutes` with missing/ONGOING status as ABANDONED.
        Returns the number of rows updated (0 on error).
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            cutoff_iso = cutoff.replace(microsecond=0).isoformat()
            with self._lock, self._db:
                cur = self._db.cursor()
                cur.execute(
                    """
                    UPDATE games
                    SET status='ABANDONED', ended_at=?, last_seen=?
                    WHERE (status IS NULL OR status='ONGOING') AND last_seen < ?
                    """,
                    (cutoff_iso, cutoff_iso, cutoff_iso),
                )
                return cur.rowcount
        except Exception as e:
            log.exception(f"DB prune_abandoned failed: {e}")
            return 0

    def increment_move(self, *, game_id: str, kind: str):
        """
        Increment counters for moves.
        kind: 'measure' | 'gate'
        """
        try:
            with self._lock, self._db:
                if kind == "measure":
                    self._db.execute(
                        "UPDATE games SET moves_measures = moves_measures + 1 WHERE game_id=?",
                        (game_id,),
                    )
                elif kind == "gate":
                    self._db.execute(
                        "UPDATE games SET moves_gates = moves_gates + 1 WHERE game_id=?",
                        (game_id,),
                    )
                else:
                    # Unknown kind: ignore but log (keeps server simple)
                    log.warning(f"increment_move: unknown kind '{kind}' gid={game_id}")
        except Exception as e:
            log.exception(f"DB increment_move failed gid={game_id}, kind={kind}: {e}")

    # --- analytics / counters ---
    def online_active(self, *, minutes: int = 30) -> int:
        """
        Return the number of *active* ONGOING games in the last `minutes`.
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            cutoff_iso = cutoff.replace(microsecond=0).isoformat()
            with self._lock:
                cur = self._db.cursor()
                cur.execute(
                    "SELECT COUNT(*) AS n FROM games WHERE last_seen >= ? AND status='ONGOING'",
                    (cutoff_iso,),
                )
                row = cur.fetchone()
                return int(row["n"] if row else 0)
        except Exception as e:
            log.exception(f"DB online_active failed: {e}")
            return 0

    def summary(self) -> Dict[str, Any]:
        """Basic aggregate counts (0s on error)."""
        out = {"total_games": 0, "wins": 0, "losses": 0, "unique_users": 0}
        try:
            with self._lock:
                cur = self._db.cursor()
                cur.execute("SELECT COUNT(*) n FROM games")
                out["total_games"] = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) n FROM games WHERE status='WIN'")
                out["wins"] = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(*) n FROM games WHERE status='LOST'")
                out["losses"] = int(cur.fetchone()["n"])
                cur.execute("SELECT COUNT(DISTINCT user_id) n FROM games WHERE user_id!=''")
                out["unique_users"] = int(cur.fetchone()["n"])
        except Exception as e:
            log.exception(f"DB summary failed: {e}")
        return out

    # --- admin reads / export ---
    def game_columns(self) -> list[str]:
        """
        Column names of the `games` table, in declaration order.

        Read from the table definition rather than from a result row so callers
        get a stable header even when there are no rows to describe.
        """
        try:
            with self._lock:
                cur = self._db.cursor()
                cur.execute("PRAGMA table_info(games)")
                return [str(row["name"]) for row in cur.fetchall()]
        except Exception as e:
            log.exception(f"DB game_columns failed: {e}")
            return []

    def recent_games(self, *, limit: int = 100) -> list[Dict[str, Any]]:
        """
        The `limit` most recently created games, newest first.

        Returns plain dicts rather than `sqlite3.Row` objects so callers do not
        depend on the connection's row factory. Empty list on error.
        """
        try:
            with self._lock:
                cur = self._db.cursor()
                cur.execute("SELECT * FROM games ORDER BY created_at DESC LIMIT ?", (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            log.exception(f"DB recent_games failed: {e}")
            return []

    def export_games(self) -> tuple[list[str], list[list[Any]]]:
        """
        Every game row as `(columns, rows)`, ready for CSV export.

        Each row is ordered to match `columns`, and the columns are reported
        even when there are no rows, so an export of an empty database still
        carries a valid header line.
        """
        # Taken before the lock below: threading.Lock is not reentrant, so this
        # must not run inside the read block.
        columns = self.game_columns()
        try:
            with self._lock:
                cur = self._db.cursor()
                cur.execute("SELECT * FROM games")
                rows = [[row[name] for name in columns] for row in cur.fetchall()]
            return columns, rows
        except Exception as e:
            log.exception(f"DB export_games failed: {e}")
            return columns, []

    # --- persisted application settings ---
    def load_app_settings(self) -> Dict[str, Any]:
        """Return dashboard-owned settings, ignoring malformed stored values."""
        out: Dict[str, Any] = {}
        try:
            with self._lock:
                rows = self._db.execute("SELECT key, value FROM app_settings").fetchall()
            for row in rows:
                try:
                    out[str(row["key"])] = json.loads(str(row["value"]))
                except (TypeError, ValueError):
                    log.warning(f"Ignoring malformed persisted setting {row['key']!r}")
        except Exception as e:
            log.exception(f"DB load_app_settings failed: {e}")
        return out

    def save_app_settings(self, values: Dict[str, Any]) -> bool:
        """Atomically replace the dashboard-owned settings snapshot."""
        try:
            rows = [(str(key), json.dumps(value)) for key, value in values.items()]
            with self._lock, self._db:
                self._db.execute("DELETE FROM app_settings")
                self._db.executemany("INSERT INTO app_settings (key, value) VALUES (?, ?)", rows)
            return True
        except Exception as e:
            log.exception(f"DB save_app_settings failed: {e}")
            return False


# ---------- Singleton accessor ----------

@lru_cache(maxsize=1)
def get_store() -> SQLiteStore:
    path = default_db_path()
    log.info(f"Opening SQLite database at {path}")
    return SQLiteStore(path)
