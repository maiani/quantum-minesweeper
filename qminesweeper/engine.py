# qminesweeper/engine.py
"""
Framework-free game engine contract shared by the server routes and the future
in-browser (Pyodide) engine.

- `serialize_game` is the read side: a lean game-state **dict** (game data only;
  no presentation, no config).
- `Command` + `apply_command` are the write side: a structured command applied
  to a live game.
- `parse_command` is a string adapter for the existing form route; the browser
  engine builds `Command`s directly and does not use it.

This module imports only board/game/quantum (pure Python + numpy) — no FastAPI,
no settings — so it loads under Pyodide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import GameStatus, QMineSweeperGame
from qminesweeper.quantum_backend import ONE_QUBIT_GATES, TWO_QUBIT_GATES

# Upper-cased move tokens, derived from the shared arity sets.
_SINGLE_Q = {g.value.upper() for g in ONE_QUBIT_GATES}
_TWO_Q = {g.value.upper() for g in TWO_QUBIT_GATES}
_RC = re.compile(r"^\s*(\d+)\s*,\s*(\d+)\s*$")


def serialize_game(board: QMineSweeperBoard, game: QMineSweeperGame, game_id: str) -> dict:
    """The game-state contract: game data only.

    `grid` uses board.export_numeric_grid()'s encoding (-1 unexplored, -2 pinned,
    9 mine, else clue). Presentation (symbols, colours, labels) and config
    (feature flags) are NOT here — the frontend owns those.
    """
    return {
        "game_id": game_id,
        "rows": board.rows,
        "cols": board.cols,
        "grid": board.export_numeric_grid().tolist(),
        "status": game.status.name,
        "win_condition": game.cfg.win_condition.name,
        "moveset": game.cfg.move_set.name,
        "mines_exp": board.expected_mines(),
        "ent_measure": board.entanglement_score("mean") * board.n,
    }


@dataclass(frozen=True)
class Command:
    """A single command applied to a live game. Cells are 0-based (row, col)."""

    kind: str  # "measure" | "pin" | "gate" | "reset"
    cell: Optional[tuple[int, int]] = None
    cell2: Optional[tuple[int, int]] = None  # second target for two-qubit gates
    gate: Optional[str] = None  # gate token, for kind == "gate"


def _rc(token: str) -> tuple[int, int]:
    m = _RC.match(token)
    if not m:
        raise ValueError(f"Bad coord '{token}' (expected 'r,c')")
    return int(m.group(1)) - 1, int(m.group(2)) - 1


def parse_command(cmd: str) -> Command:
    """Parse a move-command string (form-route adapter) into a Command."""
    if not cmd or not cmd.strip():
        raise ValueError("Empty command")
    s = cmd.strip()
    if _RC.match(s):
        return Command("measure", cell=_rc(s))
    parts = s.split()
    op = parts[0].upper()
    if op == "M" and len(parts) == 2:
        return Command("measure", cell=_rc(parts[1]))
    if op == "P" and len(parts) == 2:
        return Command("pin", cell=_rc(parts[1]))
    if op in _SINGLE_Q and len(parts) == 2:
        return Command("gate", gate=op, cell=_rc(parts[1]))
    if op in _TWO_Q and len(parts) == 3:
        return Command("gate", gate=op, cell=_rc(parts[1]), cell2=_rc(parts[2]))
    raise ValueError(f"Unrecognized command: '{cmd}'")


def apply_command(board: QMineSweeperBoard, game: QMineSweeperGame, cmd: Command) -> None:
    """Apply a command to a live game (mutates board/game in place)."""
    if cmd.kind == "measure":
        game.cmd_measure(*cmd.cell)
    elif cmd.kind == "pin":
        game.cmd_toggle_pin(*cmd.cell)
    elif cmd.kind == "gate":
        targets = [cmd.cell] if cmd.cell2 is None else [cmd.cell, cmd.cell2]
        game.cmd_gate(cmd.gate, targets)
    elif cmd.kind == "reset":
        board.reset()
        game.status = GameStatus.ONGOING
    else:
        raise ValueError(f"Unknown command kind: {cmd.kind!r}")
