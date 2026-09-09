# qminesweeper/engine.py
"""
Framework-free game engine contract shared by the server routes and the
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
from qminesweeper.game import ALLOWED_MOVES, Action, GameConfig, GameStatus, MoveSet, QMineSweeperGame, WinCondition
from qminesweeper.quantum_backend import ONE_QUBIT_GATES, TWO_QUBIT_GATES, QuantumBackend, QuantumGate

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


def _validate_probe_area(area: list[int], n: int, name: str) -> list[int]:
    if not isinstance(area, list) or not area:
        raise ValueError(f"{name} must be a nonempty list")
    if any(isinstance(i, bool) or not isinstance(i, int) for i in area):
        raise ValueError(f"{name} must contain integers")
    if len(set(area)) != len(area):
        raise ValueError(f"{name} contains duplicate cells")
    if any(i < 0 or i >= n for i in area):
        raise ValueError(f"{name} contains an out-of-range cell")
    return area


PROBE_REGION_LIMIT = 2
"""How many probe regions the diagnostic implements: A, and optionally B."""

PROBE_REGION_DEFAULT = 2
"""The region count setup uses unless the player chooses another.

This is a game tier, not a deployment switch: whether probes exist at all is
the separate `ENABLE_ENTANGLEMENT_PROBES` application flag. Simple Setup gives
entangled boards this many regions; Advanced Setup can pick any count up to
``PROBE_REGION_LIMIT``.
"""


def probe_rules_for_regions(regions: int, region_limit: int) -> tuple[bool, bool]:
    """Per-game probe rules for a requested region count.

    ``regions`` is what setup asked for and ``region_limit`` what the deployment
    allows; the smaller wins, and neither can exceed ``PROBE_REGION_LIMIT``.
    0 means no probes, 1 region A alone, 2 also region B.
    """
    allowed = max(0, min(int(regions), int(region_limit), PROBE_REGION_LIMIT))
    return allowed >= 1, allowed >= 2


def probe_rules_for_limit(
    entanglement_probes: bool,
    two_area_probes: bool,
    region_limit: int,
) -> tuple[bool, bool]:
    """Narrow a game's requested probe rules to a deployment's region limit.

    The boolean form of :func:`probe_rules_for_regions`, for callers holding a
    game's stored rules rather than a setup choice. A request beyond the limit
    is narrowed rather than rejected, so neither a stale setup form nor a
    hand-made request can enable more than the deployment allows.
    """
    requested = 0
    if entanglement_probes:
        requested = 2 if two_area_probes else 1
    return probe_rules_for_regions(requested, region_limit)


def probe_regions(
    board: QMineSweeperBoard,
    game: QMineSweeperGame,
    area_a: list[int],
    area_b: list[int] | None = None,
) -> dict:
    """Read region entropies from a game without changing its state."""
    if not isinstance(game.cfg.entanglement_probes, bool) or not game.cfg.entanglement_probes:
        raise ValueError("entanglement probes are disabled")
    a = _validate_probe_area(area_a, board.n, "area_a")
    b = None if area_b is None else _validate_probe_area(area_b, board.n, "area_b")
    if b is not None:
        if not isinstance(game.cfg.two_area_probes, bool) or not game.cfg.two_area_probes:
            raise ValueError("two-area probes are disabled")
        if set(a) & set(b):
            raise ValueError("probe regions must not overlap")
    entropy_a = float(board.state.entanglement_entropy(a))
    entropy_b = None if b is None else float(board.state.entanglement_entropy(b))
    entropy_union = None
    mutual_information = None
    if b is not None:
        entropy_union = float(board.state.entanglement_entropy(a + b))
        mutual_information = entropy_a + entropy_b - entropy_union
    return {
        "entropy_a": entropy_a,
        "entropy_b": entropy_b,
        "entropy_union": entropy_union,
        "mutual_information": mutual_information,
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


def command_tokens_for_moveset(move_set: MoveSet) -> dict[str, list[str]]:
    """Return command tokens allowed by ``move_set``, grouped by arity.

    The rules live in :data:`game.ALLOWED_MOVES`, while gate arity lives in
    :mod:`quantum_backend`. Controllers such as the TUI use this derived view
    for prompts; they must not maintain their own gate or move-set lists.
    """
    allowed = ALLOWED_MOVES[move_set]
    return {
        "actions": [action.value for action in Action if action in allowed],
        "single": [gate.value.upper() for gate in QuantumGate if gate in allowed and gate in ONE_QUBIT_GATES],
        "two": [gate.value.upper() for gate in QuantumGate if gate in allowed and gate in TWO_QUBIT_GATES],
    }


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


# ---------- setup validation + game construction (framework-free) ----------
# Bounds for setup parameters. UI presets stay well within these; the caps exist
# so a hostile or fat-fingered request can't allocate, e.g., a 10^5 x 10^5 board.
MAX_DIM = 40
MAX_QUBITS = 1024
MAX_ENT_LEVEL = 10

# String (form/UI) values -> enums, shared by the server route and the browser.
WIN_CONDITIONS = {
    "clear": WinCondition.CLEAR,
    "identify": WinCondition.IDENTIFY,
    "sandbox": WinCondition.SANDBOX,
}
MOVE_SETS = {
    "classic": MoveSet.CLASSIC,
    "one": MoveSet.ONE_QUBIT,
    "one_complete": MoveSet.ONE_QUBIT_COMPLETE,
    "two": MoveSet.TWO_QUBIT,
    "two_extended": MoveSet.TWO_QUBIT_EXTENDED,
}


def validate_setup_params(
    rows: int,
    cols: int,
    mines: int,
    ent_level: int,
    entanglement_probes: bool = True,
    two_area_probes: bool = False,
) -> None:
    """Validate setup parameters, raising ValueError with a user-facing message."""
    if not (1 <= rows <= MAX_DIM) or not (1 <= cols <= MAX_DIM):
        raise ValueError(f"Board dimensions must be between 1 and {MAX_DIM} (got {rows}x{cols}).")
    if rows * cols > MAX_QUBITS:
        raise ValueError(f"Board too large: {rows}x{cols} exceeds {MAX_QUBITS} cells.")
    if not (0 <= ent_level <= MAX_ENT_LEVEL):
        raise ValueError(f"Entanglement level must be between 0 and {MAX_ENT_LEVEL} (got {ent_level}).")
    if not (0 <= mines <= rows * cols):
        raise ValueError(f"Mines must be between 0 and {rows * cols} (got {mines}).")
    if not isinstance(entanglement_probes, bool) or not isinstance(two_area_probes, bool):
        raise ValueError("Probe settings must be boolean")


def build_game(
    backend: QuantumBackend,
    rows: int,
    cols: int,
    mines: int,
    ent_level: int,
    win: WinCondition,
    moves: MoveSet,
    entanglement_probes: bool = True,
    two_area_probes: bool = False,
) -> tuple[QMineSweeperBoard, QMineSweeperGame]:
    """Construct (board, game) on the given backend. Validates params first.

    Used by the server (with its configured backend) and by the browser session
    (with ChppyBackend) — single source of game construction.
    """
    validate_setup_params(rows, cols, mines, ent_level, entanglement_probes, two_area_probes)
    board = QMineSweeperBoard(rows, cols, backend=backend, flood_fill=True)
    if ent_level == 0:
        board.span_classical_mines(mines)
    else:
        board.span_random_stabilizer_mines(mines, level=ent_level)
    board.set_clue_basis("Z")
    game = QMineSweeperGame(
        board,
        GameConfig(
            win_condition=win,
            move_set=moves,
            entanglement_probes=entanglement_probes,
            two_area_probes=two_area_probes,
        ),
    )
    return board, game
