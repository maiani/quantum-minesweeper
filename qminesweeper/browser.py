# qminesweeper/browser.py
"""
In-browser game session for the Pyodide build.

This is the client-side counterpart to the server's request handlers: it holds
the current game in memory and turns setup / move / reset / new-game requests
into the same game-state dict the server returns (`engine.serialize_game`). The
JS `PyodideEngine` (static/scripts/pyodide-engine.js) drives this and feeds the
result to the same `render.js`.

It is deliberately framework-free and Stim-free — only board/game/engine +
`PurePyBackend` — so it imports and runs under Pyodide. There is no server,
no auth, and no analytics DB here; just one game at a time. The page keeps that
game in memory while running and can export/import a small versioned snapshot so
the browser build can restore after a reload.
"""

from __future__ import annotations

import numpy as np

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.engine import (
    MOVE_SETS,
    WIN_CONDITIONS,
    Command,
    apply_command,
    build_game,
    parse_command,
    serialize_game,
)
from qminesweeper.game import GameConfig, GameStatus, QMineSweeperGame
from qminesweeper.purepy_backend import PurePyBackend, PurePyState

# A fixed id is fine: the browser session only ever holds one game.
_GAME_ID = "browser"
SAVE_VERSION = 1


class BrowserSession:
    """Holds the current browser game and returns serialized state after each op."""

    def __init__(self) -> None:
        self._backend = PurePyBackend()
        self._board = None
        self._game = None
        self._params: tuple | None = None  # remembered for new_same

    # ---------- lifecycle ----------
    def setup(self, rows: int, cols: int, mines: int, ent_level: int, win: str, moves: str) -> dict:
        """Start a new game from the same string params the setup form uses."""
        self._params = (rows, cols, mines, ent_level, win, moves)
        self._board, self._game = build_game(
            self._backend,
            rows,
            cols,
            mines,
            ent_level,
            WIN_CONDITIONS.get(win.lower(), WIN_CONDITIONS["identify"]),
            MOVE_SETS.get(moves.lower(), MOVE_SETS["classic"]),
        )
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
            apply_command(self._board, self._game, parse_command(cmd))
        except Exception:
            # Mirror the server: an illegal/garbled command is a silent no-op.
            pass
        return self.state()

    def reset(self) -> dict:
        self._require_game()
        apply_command(self._board, self._game, Command("reset"))
        return self.state()

    # ---------- read ----------
    def state(self) -> dict:
        self._require_game()
        return serialize_game(self._board, self._game, _GAME_ID)

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
        if not isinstance(self._board.state, PurePyState):
            raise TypeError("browser saves require PurePyState")
        rows, cols, mines, ent_level, win, moves = self._params
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
        }

    def import_save(self, snapshot: dict) -> dict:
        """Restore a save snapshot and return the restored game state."""
        if not isinstance(snapshot, dict) or snapshot.get("version") != SAVE_VERSION:
            raise ValueError("unsupported browser save format")
        params = snapshot["params"]
        rows = int(params["rows"])
        cols = int(params["cols"])
        mines = int(params["mines"])
        ent_level = int(params["ent_level"])
        win = str(params["win"])
        moves = str(params["moves"])
        self._params = (rows, cols, mines, ent_level, win, moves)

        win_enum = WIN_CONDITIONS.get(win.lower(), WIN_CONDITIONS["identify"])
        move_enum = MOVE_SETS.get(moves.lower(), MOVE_SETS["classic"])
        board = QMineSweeperBoard(rows, cols, backend=self._backend, flood_fill=bool(snapshot["board"]["flood_fill"]))
        board.set_preparation([(str(gate), [int(t) for t in targets]) for gate, targets in snapshot["board"]["prep"]])
        board.set_clue_basis(str(snapshot["board"]["clue_basis"]))

        tableau = snapshot["tableau"]
        state = board.state
        if not isinstance(state, PurePyState) or int(tableau["n"]) != state.n:
            raise ValueError("save does not match board size")
        state.x[:, :] = np.array(tableau["x"], dtype=np.uint8)
        state.z[:, :] = np.array(tableau["z"], dtype=np.uint8)
        state.r[:] = np.array(tableau["r"], dtype=np.uint8)

        board._exploration[:, :] = np.array(snapshot["board"]["exploration"], dtype=np.int8)
        board._measured = {int(idx): int(outcome) for idx, outcome in snapshot["board"]["measured"]}

        game = QMineSweeperGame(board, GameConfig(win_condition=win_enum, move_set=move_enum))
        game.status = GameStatus[str(snapshot["status"])]
        self._board = board
        self._game = game
        return self.state()

    def _require_game(self) -> None:
        if self._game is None:
            raise RuntimeError("no active game; call setup() first")
