"""Game work runs off the event loop, one request at a time per game."""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest
from starlette.requests import Request

from qminesweeper import server


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/move", "headers": []})


def _add_game(gid: str) -> None:
    board, game = server.build_board_and_game(2, 2, 0, 0, server.WinCondition.SANDBOX, server.MoveSet.TWO_QUBIT)
    server.GAMES[gid] = {"board": board, "game": game, "config": {}, "last_seen": None}


def _peak_concurrent_moves(monkeypatch: pytest.MonkeyPatch, game_ids: list[str]) -> int:
    """Send one slow move per id at once; return how many ever ran together."""
    active = 0
    peak = 0
    guard = threading.Lock()
    real_apply = server.apply_command

    def slow_apply(board, game, command):
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        time.sleep(0.2)
        with guard:
            active -= 1
        return real_apply(board, game, command)

    monkeypatch.setattr(server, "apply_command", slow_apply)

    async def run() -> None:
        await asyncio.gather(*(server.move_post(_request(), cmd="H 1,1", game_id=gid) for gid in game_ids))

    for gid in set(game_ids):
        _add_game(gid)
    try:
        asyncio.run(run())
    finally:
        for gid in set(game_ids):
            server.GAMES.pop(gid, None)
            server._GAME_LOCKS.pop(gid, None)
    return peak


def test_moves_on_one_game_never_overlap(monkeypatch):
    """A double click must not interleave two mutations of one board."""
    assert _peak_concurrent_moves(monkeypatch, ["lock-same", "lock-same"]) == 1


def test_moves_on_different_games_run_concurrently(monkeypatch):
    """The work is in worker threads, so one slow game does not hold up another."""
    assert _peak_concurrent_moves(monkeypatch, ["lock-a", "lock-b"]) == 2


def test_pruning_a_game_drops_its_lock():
    gid = "lock-stale"
    _add_game(gid)
    server.GAMES[gid]["last_seen"] = datetime.now(timezone.utc) - timedelta(days=1)
    server._game_lock(gid)
    assert gid in server._GAME_LOCKS
    server.prune_stale_games()
    assert gid not in server.GAMES
    assert gid not in server._GAME_LOCKS
