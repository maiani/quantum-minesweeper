from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


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
    2) /data/qms.sqlite if /data is writable (container default).
    3) ./qms_data/qms.sqlite (project-local) as a last resort.
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

    # 3) local project folder
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
            self._db.execute("""
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
              resets       INTEGER NOT NULL DEFAULT 0
            )""")
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_games_user ON games(user_id)")
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_games_last_seen ON games(last_seen)")

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
    ):
        with self._lock, self._db:
            self._db.execute(
                """
                INSERT OR REPLACE INTO games
                (game_id,user_id,created_at,last_seen,rows,cols,mines,ent_level,win_cond,moveset,prep_circuit,status,ended_at,resets)
                VALUES
                (?,?,?,?,?,?,?,?,?,?,?, 'ONGOING', NULL, 0)
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
                ),
            )

    def heartbeat(self, *, game_id: str, ts: str):
        with self._lock, self._db:
            self._db.execute("UPDATE games SET last_seen=? WHERE game_id=?", (ts, game_id))

    def outcome(self, *, game_id: str, ts: str, status: str):
        with self._lock, self._db:
            self._db.execute(
                "UPDATE games SET status=?, ended_at=?, last_seen=? WHERE game_id=?",
                (status, ts, ts, game_id),
            )

    def increment_reset(self, *, game_id: str):
        with self._lock, self._db:
            self._db.execute(
                "UPDATE games SET resets = resets + 1, status='ONGOING', ended_at=NULL WHERE game_id=?",
                (game_id,),
            )

    def prune_abandoned(self, *, minutes: int) -> int:
        """
        Mark games older than `minutes` and with missing/ONGOING status as ABANDONED.
        Returns the number of rows updated.
        """
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

    # --- analytics / counters ---
    def online_active(self, *, minutes: int = 30) -> int:
        """
        Return the number of *active* games in the last `minutes`, excluding finished ones.
        """
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

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            cur = self._db.cursor()
            cur.execute("SELECT COUNT(*) n FROM games")
            total_games = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) n FROM games WHERE status='WIN'")
            wins = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) n FROM games WHERE status='LOST'")
            losses = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(DISTINCT user_id) n FROM games WHERE user_id!=''")
            unique_users = int(cur.fetchone()["n"])
            return {"total_games": total_games, "wins": wins, "losses": losses, "unique_users": unique_users}


# ---------- Singleton accessor ----------


@lru_cache(maxsize=1)
def get_store() -> SQLiteStore:
    return SQLiteStore(default_db_path())
