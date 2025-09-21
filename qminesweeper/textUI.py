# qminesweeper/textUI.py
from __future__ import annotations
from typing import Tuple, List, Dict
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.text import Text

from qminesweeper.board import QMineSweeperBoard, CellState
from qminesweeper.game import (
    QMineSweeperGame, GameConfig, WinCondition, MoveSet, GameStatus, MoveType
)
from qminesweeper.quantum_backend import QuantumBackend  # interface

console = Console()

# ---------- Coloring helper for fractional clues ----------
def clue_style(val: float) -> str:
    v = min(max(val / 8.0, 0.0), 1.0)
    r = int(255 * v)
    g = int(255 * (1 - v))
    return f"rgb({r},{g},0)"


def render_rich(board: QMineSweeperBoard, prec: int = 1):
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column(" ", justify="right")
    for col in range(1, board.cols + 1):
        table.add_column(Text(str(col)), justify="center")

    grid = board.export_numeric_grid()
    for r in range(board.rows):
        row = [Text(str(r + 1))]
        for c in range(board.cols):
            val = grid[r, c]
            if val == -1:
                cell = Text("■", style="dim")
            elif val == -2:
                cell = Text("⚑", style="yellow")
            elif val == 9.0:
                cell = Text("💥", style="bold red")
            elif val == 0.0:
                cell = Text(" ", style="on black")
            else:
                cell = Text(f"{val:.{prec}f}", style=clue_style(val))
            row.append(cell)
        table.add_row(*row)

    console.clear()
    console.print(table)


# ---------- Setup flow ----------
def welcome_screen():
    console.clear()
    console.print("[bold magenta]Quantum Minesweeper — Advanced Setup[/bold magenta]")


def ask_int(prompt: str, cond=lambda x: True) -> int:
    while True:
        try:
            v = int(console.input(prompt).strip())
            if cond(v):
                return v
        except ValueError:
            pass
        console.print("[red]Invalid input.[/]")


def advanced_setup() -> Tuple[WinCondition, MoveSet, int, int, int, int]:
    console.print("[bold]Win condition:[/]\n"
                  "  [cyan]1.[/] Identify (classic: lose on measuring a mine, win when all safe cells are explored)\n"
                  "  [cyan]2.[/] Clear (all mine probabilities ~ 0)")
    w_choice = ask_int("Choice [1-2]: ", lambda x: x in (1, 2))
    win = WinCondition.IDENTIFY if w_choice == 1 else WinCondition.CLEAR

    console.print("[bold]Move set:[/]\n"
                  "  [cyan]1.[/] Classic (Measure, Pin)\n"
                  "  [cyan]2.[/] One-qubit (X,Y,Z,H,S)\n"
                  "  [cyan]3.[/] One-qubit (complete: +Sdg,SX,SXdg,SY,SYdg)\n"
                  "  [cyan]4.[/] Two-qubit (adds CX,CY,CZ,SWAP)")
    m_choice = ask_int("Choice [1-4]: ", lambda x: x in (1, 2, 3, 4))
    move = {
        1: MoveSet.CLASSIC,
        2: MoveSet.ONE_QUBIT,
        3: MoveSet.ONE_QUBIT_COMPLETE,
        4: MoveSet.TWO_QUBIT,
    }[m_choice]

    rows = ask_int("Rows: ", lambda x: x > 0)
    cols = ask_int("Cols: ", lambda x: x > 0)
    mines = ask_int("Mines: ", lambda x: 0 < x < rows * cols)
    ent_level = ask_int("Entanglement level (0=classical, >=1 stabilizers): ", lambda x: x >= 0)

    return win, move, rows, cols, mines, ent_level


def make_board(backend: QuantumBackend, rows: int, cols: int, mines: int,
               ent_level: int, basis: str = "Z", flood: bool = True) -> QMineSweeperBoard:
    board = QMineSweeperBoard(rows, cols, backend=backend, flood_fill=flood)
    if ent_level == 0:
        board.span_classical_mines(mines)
    else:
        board.span_random_stabilizer_mines(nmines=mines, level=ent_level)
    board.set_clue_basis(basis)
    return board


# ---------- Allowed tools computation & prompt ----------
TOKEN_TO_MOVE: Dict[str, MoveType] = {
    "M": MoveType.MEASURE, "P": MoveType.PIN_TOGGLE,
    "X": MoveType.X_GATE, "Y": MoveType.Y_GATE, "Z": MoveType.Z_GATE,
    "H": MoveType.H_GATE, "S": MoveType.S_GATE, "SDG": MoveType.SDG_GATE,
    "SX": MoveType.SX_GATE, "SXDG": MoveType.SXDG_GATE,
    "SY": MoveType.SY_GATE, "SYDG": MoveType.SYDG_GATE,
    "CX": MoveType.CX_GATE, "CY": MoveType.CY_GATE,
    "CZ": MoveType.CZ_GATE, "SWAP": MoveType.SWAP_GATE,
}
ONE_QUBIT_BASIC: List[str] = ["X", "Y", "Z", "H", "S"]
ONE_QUBIT_EXTRA: List[str] = ["SDG", "SX", "SXDG", "SY", "SYDG"]
TWO_QUBIT_TOKENS: List[str] = ["CX", "CY", "CZ", "SWAP"]

def allowed_tokens_for_moveset(ms: MoveSet) -> Dict[str, List[str]]:
    """
    Returns dict with keys: 'mp' (measure/pin), 'single', 'two'
    listing the tokens allowed for the given MoveSet.
    """
    tokens = {"mp": ["M", "P"], "single": [], "two": []}
    if ms == MoveSet.CLASSIC:
        return tokens
    if ms == MoveSet.ONE_QUBIT:
        tokens["single"] = ONE_QUBIT_BASIC[:]
    elif ms == MoveSet.ONE_QUBIT_COMPLETE:
        tokens["single"] = ONE_QUBIT_BASIC + ONE_QUBIT_EXTRA
    elif ms == MoveSet.TWO_QUBIT:
        tokens["single"] = ONE_QUBIT_BASIC + ONE_QUBIT_EXTRA
        tokens["two"] = TWO_QUBIT_TOKENS[:]
    return tokens

def build_prompt(tokens: Dict[str, List[str]]) -> str:
    parts = []
    if tokens["mp"]:
        parts.append(f"[{ '/'.join(tokens['mp'])}] r,c")
    if tokens["single"]:
        parts.append(f"[{ '/'.join(tokens['single'])}] r,c")
    if tokens["two"]:
        parts.append(f"[{ '/'.join(tokens['two'])}] r1,c1 r2,c2")
    parts.append("R")
    parts.append("N")
    parts.append("Q")
    return "([ " + " | ".join(parts) + " ]): "


def game_loop(board: QMineSweeperBoard, game: QMineSweeperGame):
    """
    Main gameplay loop with a post-game menu that honors:
      - R: reset SAME board (same preparation, same rules) — no questions
      - S: start NEW board with SAME rules (re-sample preparation) — no questions
      - N: go to Advanced Setup (ask questions)
      - Q: quit
    """
    tokens = allowed_tokens_for_moveset(game.cfg.move_set)

    while True:
        # ---- live gameplay until win/lose ----
        render_rich(board)
        console.print(
            "[dim]Tip: entering 'r,c' without a command performs a Measure (M).[/dim]"
        )

        while game.status == GameStatus.ONGOING:
            try:
                raw = console.input(
                    "[yellow]Your move[/] " + build_prompt(tokens)
                ).strip()
                if not raw:
                    continue

                u = raw.upper()
                if u in ("Q", "QUIT", "EXIT"):
                    console.print("[italic]Game exited.[/]")
                    return "QUIT"
                if u == "R":
                    # live reset: same board & rules, no questions
                    board.reset()
                    game.status = GameStatus.ONGOING
                    render_rich(board)
                    console.print("[green]Board reset.[/]")
                    continue
                if u == "N":
                    return "NEW_RULES"

                parts = u.split()
                cmd = parts[0]

                # Two-qubit gate
                if cmd in tokens["two"]:
                    if len(parts) != 3:
                        console.print(f"[red]Format: {cmd} r1,c1 r2,c2[/]")
                        continue
                    try:
                        r1, c1 = map(int, parts[1].split(","))
                        r2, c2 = map(int, parts[2].split(","))
                    except ValueError:
                        console.print("[red]Invalid coordinates. Use row,col.[/]")
                        continue
                    game.cmd_gate(cmd, [(r1 - 1, c1 - 1), (r2 - 1, c2 - 1)])

                else:
                    # Single-qubit or measure/pin
                    if cmd in tokens["mp"] or cmd in tokens["single"]:
                        if len(parts) < 2:
                            console.print(f"[red]Format: {cmd} row,col[/]")
                            continue
                        pos = parts[1]
                        try:
                            r, c = map(int, pos.split(","))
                        except ValueError:
                            console.print("[red]Invalid coordinates. Use row,col.[/]")
                            continue

                        if cmd == "P":
                            game.cmd_toggle_pin(r - 1, c - 1)
                        elif cmd == "M" or cmd in ONE_QUBIT_BASIC + ONE_QUBIT_EXTRA:
                            if cmd == "M":
                                game.cmd_measure(r - 1, c - 1)
                            else:
                                # Single-qubit gate must be explicitly allowed
                                if cmd not in tokens["single"]:
                                    console.print(f"[red]{cmd} not allowed in this MoveSet.[/]")
                                    continue
                                game.cmd_gate(cmd, [(r - 1, c - 1)])
                        else:
                            console.print(f"[red]Unknown command: {cmd}[/]")
                            continue

                    else:
                        # If it's not a known token, try default "measure" syntax r,c — only if Measure is allowed
                        if "M" in tokens["mp"]:
                            try:
                                r, c = map(int, cmd.split(","))
                            except ValueError:
                                console.print("[red]Unknown or disallowed command.[/]")
                                continue
                            game.cmd_measure(r - 1, c - 1)
                        else:
                            console.print("[red]Unknown or disallowed command.[/]")
                            continue

                render_rich(board)
                console.print(f"[cyan]Game status:[/] [bold]{game.status.name}[/]")

            except Exception as e:
                console.print(f"[red]Invalid input:[/] {e}")

        # ---- end-game menu ----
        console.print("[bold]Game over![/bold]")
        console.print(
            "Choose: [bold]N[/] new setup · [bold]S[/] same setup (new mines) · "
            "[bold]R[/] reset board · [bold]Q[/] quit"
        )
        while True:
            choice = console.input("[yellow]Post-game[/] (N/S/R/Q): ").strip().upper()
            if choice == "Q":
                return "QUIT"
            elif choice == "N":
                return "NEW_RULES"
            elif choice == "S":
                # handled by run_tui (new board, same rules)
                return "SAME_RULES"
            elif choice == "R":
                board.reset()
                game.status = GameStatus.ONGOING
                render_rich(board)
                break
            else:
                console.print("[red]Invalid choice.[/]")
        # loop continues: gameplay resumes


def run_tui(backend: QuantumBackend):
    welcome_screen()
    while True:
        win, move, rows, cols, mines, ent_level = advanced_setup()

        while True:
            board = make_board(backend, rows, cols, mines, ent_level, basis="Z", flood=True)
            game = QMineSweeperGame(board, GameConfig(win_condition=win, move_set=move))

            outcome = game_loop(board, game)
            if outcome == "QUIT":
                return
            if outcome == "NEW_RULES":
                break
            if outcome == "SAME_RULES":
                continue

