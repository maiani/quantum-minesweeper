# qminesweeper/browser.py
"""
In-browser game session for the Pyodide build.

This is the client-side counterpart to the server's request handlers: it holds
the current game in memory and turns setup / move / reset / new-game requests
into the same game-state dict the server returns (`engine.serialize_game`). The
JS `PyodideEngine` (static/scripts/pyodide-engine.js) drives this and feeds the
result to the same `render.js`.

It is deliberately framework-free and Stim-free — only board/game/engine +
`ChppyBackend` — so it imports and runs under Pyodide. There is no server, no
auth, and no database here; just one game at a time. The page keeps that game in
memory while running and can export/import a small versioned snapshot so the
browser build can restore after a reload.

It does keep a per-game analytics record mirroring the row the server writes for
its own games, so a browser-only session can report the same statistics when the
page is configured to and has connectivity. Nothing here transmits: the record
is data the page may choose to send. See `analytics_record`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import numpy as np

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.chppy_backend import ChppyBackend, ChppyState
from qminesweeper.engine import (
    MOVE_SETS,
    WIN_CONDITIONS,
    Command,
    apply_command,
    build_game,
    parse_command,
    probe_regions,
    serialize_game,
)
from qminesweeper.game import GameConfig, GameStatus, QMineSweeperGame

# A fixed id is fine: the browser session only ever holds one game.
_GAME_ID = "browser"
SAVE_VERSION = 1


class BrowserSession:
    """Holds the current browser game and returns serialized state after each op."""

    def __init__(self) -> None:
        self._backend = ChppyBackend()
        self._board = None
        self._game = None
        self._params: tuple | None = None  # remembered for new_same
        self._analytics: dict | None = None

    # ---------- analytics ----------
    # A browser-only session has no server recording what it plays. These
    # helpers keep the same fields the server's analytics row holds, with the
    # same rules: pins are not counted, a reset zeroes the move counters and
    # increments `resets`, and the outcome is observed on the move that ends the
    # game. Keeping the semantics identical is what makes the two sources
    # comparable once reported.

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _touch(self) -> None:
        """Stamp activity and capture a terminal outcome, as the server does."""
        if self._analytics is None:
            return
        now = self._now()
        self._analytics["last_seen"] = now
        if self._game is not None and self._analytics["status"] == "ONGOING":
            if self._game.status == GameStatus.WIN:
                self._analytics.update(status="WIN", ended_at=now)
            elif self._game.status == GameStatus.LOST:
                self._analytics.update(status="LOST", ended_at=now)

    def analytics_record(self) -> dict | None:
        """The current game's statistics, shaped like the server's row.

        Returns a copy, so a caller holding it while play continues does not see
        it mutate underneath, and None before the first game.
        """
        if self._analytics is None:
            return None
        record = dict(self._analytics)
        record["prep_circuit"] = [[gate, list(targets)] for gate, targets in record["prep_circuit"]]
        return record

    # ---------- lifecycle ----------
    def setup(
        self,
        rows: int,
        cols: int,
        mines: int,
        ent_level: int,
        win: str,
        moves: str,
        entanglement_probes: bool = True,
        two_area_probes: bool = False,
    ) -> dict:
        """Start a new game from the same string params the setup form uses."""
        board, game = build_game(
            self._backend,
            rows,
            cols,
            mines,
            ent_level,
            WIN_CONDITIONS.get(win.lower(), WIN_CONDITIONS["identify"]),
            MOVE_SETS.get(moves.lower(), MOVE_SETS["classic"]),
            entanglement_probes,
            two_area_probes,
        )
        self._params = (rows, cols, mines, ent_level, win, moves, entanglement_probes, two_area_probes)
        self._board, self._game = board, game

        # Resolve the vocabulary the same way build_game did above, so the
        # record says which rules actually applied rather than what was asked.
        win_key = win.lower() if win.lower() in WIN_CONDITIONS else "identify"
        moves_key = moves.lower() if moves.lower() in MOVE_SETS else "classic"
        now = self._now()
        self._analytics = {
            # A fresh id per game, as the server mints one per /setup. Distinct
            # from the fixed serialization id, which the save format depends on.
            "game_id": str(uuid4()),
            "created_at": now,
            "last_seen": now,
            "ended_at": None,
            "rows": int(rows),
            "cols": int(cols),
            "mines": int(mines),
            "ent_level": int(ent_level),
            "win_cond": win_key,
            "moveset": moves_key,
            "status": "ONGOING",
            "prep_circuit": board.preparation_circuit,
            "resets": 0,
            "moves_measures": 0,
            "moves_gates": 0,
        }
        return self.state()

    def new_same(self) -> dict:
        """Restart with a fresh board and the same rules."""
        if self._params is None:
            raise RuntimeError("new_same called before setup")
        return self.setup(*self._params)

    # ---------- in-game commands ----------
    def move(self, cmd: str) -> dict:
        """Apply a move-command string ('2,3', 'X 1,1', 'CX 1,1 2,2'). No-op on error."""
        self._require_game()
        try:
            command = parse_command(cmd)
            apply_command(self._board, self._game, command)
            if self._analytics is not None:
                # Counted only after the command applied, and pins never count.
                if command.kind == "measure":
                    self._analytics["moves_measures"] += 1
                elif command.kind == "gate":
                    self._analytics["moves_gates"] += 1
        except Exception:
            # Mirror the server: an illegal/garbled command is a silent no-op.
            pass
        self._touch()
        return self.state()

    def reset(self) -> dict:
        self._require_game()
        apply_command(self._board, self._game, Command("reset"))
        if self._analytics is not None:
            self._analytics.update(
                resets=self._analytics["resets"] + 1,
                moves_measures=0,
                moves_gates=0,
                status="ONGOING",
                ended_at=None,
                last_seen=self._now(),
            )
        return self.state()

    # ---------- read ----------
    def state(self) -> dict:
        self._require_game()
        return serialize_game(self._board, self._game, _GAME_ID)

    def config(self) -> dict:
        self._require_game()
        return {
            "entanglement_probes": self._game.cfg.entanglement_probes,
            "two_area_probes": self._game.cfg.two_area_probes,
        }

    def probe(self, area_a: list[int], area_b: list[int] | None = None) -> dict:
        self._require_game()
        return probe_regions(self._board, self._game, area_a, area_b)

    # ---------- persistence ----------
    def export_save(self) -> dict:
        """Return a versioned browser-only save snapshot.

        The browser stores this dict in localStorage. It is a snapshot, not a
        replay log: reload restore does not depend on re-sampling random setup or
        re-playing random measurements.
        """
        self._require_game()
        if self._params is None:
            raise RuntimeError("cannot save before setup")
        if not isinstance(self._board.state, ChppyState):
            raise TypeError("browser saves require ChppyState")
        rows, cols, mines, ent_level, win, moves, entanglement_probes, two_area_probes = self._params
        state = self._board.state
        return {
            "version": SAVE_VERSION,
            "params": {
                "rows": rows,
                "cols": cols,
                "mines": mines,
                "ent_level": ent_level,
                "win": win,
                "moves": moves,
                "entanglement_probes": entanglement_probes,
                "two_area_probes": two_area_probes,
            },
            "status": self._game.status.name,
            "board": {
                "prep": self._board.preparation_circuit,
                "clue_basis": self._board.clue_basis,
                "flood_fill": self._board._flood_fill,
                "exploration": self._board._exploration.tolist(),
                "measured": [[int(idx), int(outcome)] for idx, outcome in self._board._measured.items()],
            },
            "tableau": {
                "n": state.n,
                "x": state.x.tolist(),
                "z": state.z.tolist(),
                "r": state.r.tolist(),
            },
            # Optional, and deliberately not a version bump: a save written
            # before this field existed still restores, and import treats a
            # missing record as "this game does not report". Carrying it keeps a
            # reloaded game's id and counters, so reporting it again updates the
            # same row rather than creating a second one for the same game.
            "analytics": self.analytics_record(),
        }

    def import_save(self, snapshot: dict) -> dict:
        """Restore a save snapshot and return the restored game state."""
        if not isinstance(snapshot, dict) or snapshot.get("version") != SAVE_VERSION:
            raise ValueError("unsupported browser save format")
        try:
            params = snapshot["params"]
            rows = int(params["rows"])
            cols = int(params["cols"])
            mines = int(params["mines"])
            ent_level = int(params["ent_level"])
            win = str(params["win"])
            moves = str(params["moves"])
            entanglement_probes = params.get("entanglement_probes", True)
            two_area_probes = params.get("two_area_probes", False)
            if not isinstance(entanglement_probes, bool) or not isinstance(two_area_probes, bool):
                raise ValueError("Probe settings must be boolean")

            win_enum = WIN_CONDITIONS.get(win.lower(), WIN_CONDITIONS["identify"])
            move_enum = MOVE_SETS.get(moves.lower(), MOVE_SETS["classic"])
            board = QMineSweeperBoard(
                rows,
                cols,
                backend=self._backend,
                flood_fill=bool(snapshot["board"]["flood_fill"]),
            )
            board.set_preparation(
                [(str(gate), [int(t) for t in targets]) for gate, targets in snapshot["board"]["prep"]]
            )
            board.set_clue_basis(str(snapshot["board"]["clue_basis"]))

            tableau = snapshot["tableau"]
            state = board.state
            if not isinstance(state, ChppyState) or int(tableau["n"]) != state.n:
                raise ValueError("save does not match board size")
            state.x[:, :] = np.array(tableau["x"], dtype=np.uint8)
            state.z[:, :] = np.array(tableau["z"], dtype=np.uint8)
            state.r[:] = np.array(tableau["r"], dtype=np.uint8)

            board._exploration[:, :] = np.array(snapshot["board"]["exploration"], dtype=np.int8)
            board._measured = {int(idx): int(outcome) for idx, outcome in snapshot["board"]["measured"]}

            game = QMineSweeperGame(
                board,
                GameConfig(
                    win_condition=win_enum,
                    move_set=move_enum,
                    entanglement_probes=entanglement_probes,
                    two_area_probes=two_area_probes,
                ),
            )
            game.status = GameStatus[str(snapshot["status"])]
            self._params = (rows, cols, mines, ent_level, win, moves, entanglement_probes, two_area_probes)
        except (KeyError, TypeError, IndexError, ValueError) as e:
            raise ValueError(f"malformed browser save: {e}") from e
        self._board = board
        self._game = game
        self._analytics = self._restored_analytics(snapshot.get("analytics"))
        return self.state()

    @staticmethod
    def _restored_analytics(saved: object) -> dict | None:
        """Accept an analytics record from a save, or None if it is absent or unusable.

        Saves written before analytics existed simply have no record. Rather
        than mint a fresh one, which would restart the counters and report
        numbers known to be wrong, such a game reports nothing.
        """
        if not isinstance(saved, dict) or not saved.get("game_id"):
            return None
        record = dict(saved)
        record["prep_circuit"] = [(str(gate), [int(t) for t in targets]) for gate, targets in record["prep_circuit"]]
        return record

    def _require_game(self) -> None:
        if self._game is None:
            raise RuntimeError("no active game; call setup() first")
