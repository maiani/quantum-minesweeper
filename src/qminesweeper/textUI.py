# qminesweeper/textUI.py
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.engine import Command, apply_command, command_tokens_for_moveset, parse_command
from qminesweeper.game import (
    GameConfig,
    GameStatus,
    MoveSet,
    QMineSweeperGame,
    WinCondition,
)
from qminesweeper.quantum_backend import QuantumBackend

console = Console()


# ---------- Coloring helper for fractional clues ----------
def clue_style(val: float) -> str:
    v = min(max(val / 8.0, 0.0), 1.0)
    r = int(255 * v)
    g = int(255 * (1 - v))
    return f"rgb({r},{g},0)"


def _header_stats(board: QMineSweeperBoard) -> None:
    exp_mines = board.expected_mines()
    ent_score = board.entanglement_score("mean") * board.n
    console.print(
        f"[bold magenta]⟨Mines⟩ =[/bold magenta] {exp_mines:.1f}    "
        f"[bold magenta]Local entropy sum = [/bold magenta] {int(ent_score):2d} bits"
        f"\n"
    )


def render_rich(board: QMineSweeperBoard, prec: int = 1):
    console.clear()
    _header_stats(board)

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


def ask_two_ints(prompt: str, sep: str = ",") -> tuple[int, int]:
    """
    Ask for two positive integers on one line, e.g. '5,6'.
    """
    while True:
        raw = console.input(prompt).strip()
        try:
            a_str, b_str = raw.split(sep, 1)
            a = int(a_str)
            b = int(b_str)
            if a > 0 and b > 0:
                return a, b
        except Exception:
            pass
        console.print(f"[red]Invalid input. Use the form r{sep}c like 5{sep}6[/]")


def advanced_setup() -> tuple[WinCondition, MoveSet, int, int, int, int]:
    console.print(
        "[bold]Win condition:[/]\n"
        "  [cyan]1.[/] Identify (classic: lose on measuring a mine, win when all safe cells are explored)\n"
        "  [cyan]2.[/] Clear (all mine probabilities ~ 0)"
    )
    w_choice = ask_int("Choice [1-2]: ", lambda x: x in (1, 2))
    win = WinCondition.IDENTIFY if w_choice == 1 else WinCondition.CLEAR

    move_sets = list(MoveSet)
    move_labels = {
        MoveSet.CLASSIC: "Classic",
        MoveSet.ONE_QUBIT: "One-qubit",
        MoveSet.ONE_QUBIT_COMPLETE: "One-qubit complete",
        MoveSet.TWO_QUBIT: "Two-qubit",
        MoveSet.TWO_QUBIT_EXTENDED: "Two-qubit extended",
    }
    move_lines = ["[bold]Move set:[/]"]
    for choice, move_set in enumerate(move_sets, start=1):
        tokens = command_tokens_for_moveset(move_set)
        allowed = tokens["actions"] + tokens["single"] + tokens["two"]
        move_lines.append(f"  [cyan]{choice}.[/] {move_labels[move_set]} ({','.join(allowed)})")
    console.print("\n".join(move_lines))
    m_choice = ask_int(f"Choice [1-{len(move_sets)}]: ", lambda x: 1 <= x <= len(move_sets))
    move = move_sets[m_choice - 1]

    rows, cols = ask_two_ints("Rows,Cols (e.g. 5,6): ")
    mines = ask_int("Mines: ", lambda x: 0 < x < rows * cols)
    ent_level = ask_int("Entanglement level (0=classical, >=1 stabilizers): ", lambda x: x >= 0)

    return win, move, rows, cols, mines, ent_level


def make_board(
    backend: QuantumBackend, rows: int, cols: int, mines: int, ent_level: int, basis: str = "Z", flood: bool = True
) -> QMineSweeperBoard:
    board = QMineSweeperBoard(rows, cols, backend=backend, flood_fill=flood)
    if ent_level == 0:
        board.span_classical_mines(mines)
    else:
        board.span_random_stabilizer_mines(nmines=mines, level=ent_level)
    board.set_clue_basis(basis)
    return board


# ---------- Allowed tools prompt ----------
def build_prompt(tokens: dict[str, list[str]]) -> str:
    parts = []
    if tokens["actions"]:
        parts.append(f"[{'/'.join(tokens['actions'])}] r,c")
    if tokens["single"]:
        parts.append(f"[{'/'.join(tokens['single'])}] r,c")
    if tokens["two"]:
        parts.append(f"[{'/'.join(tokens['two'])}] r1,c1 r2,c2")
    parts.extend(["R", "N", "Q"])
    return "([ " + " | ".join(parts) + " ]): "


def game_loop(board: QMineSweeperBoard, game: QMineSweeperGame):
    """
    Main gameplay loop with a post-game menu that honors:
      - R: reset SAME board (same preparation, same rules) — no questions
      - S: start NEW board with SAME rules (re-sample preparation) — no questions
      - N: go to Advanced Setup (ask questions)
      - Q: quit
    """
    tokens = command_tokens_for_moveset(game.cfg.move_set)

    while True:
        # ---- live gameplay until win/lose ----
        render_rich(board)
        console.print("[dim]Tip: entering 'r,c' without a command performs a Measure (M).[/dim]")

        while game.status == GameStatus.ONGOING:
            try:
                raw = console.input("[yellow]Your move[/] " + build_prompt(tokens)).strip()
                if not raw:
                    continue

                u = raw.upper()
                if u in ("Q", "QUIT", "EXIT"):
                    console.print("[italic]Game exited.[/]")
                    return "QUIT"
                if u == "R":
                    # live reset: same board & rules, no questions
                    apply_command(board, game, Command("reset"))
                    render_rich(board)
                    console.print("[green]Board reset.[/]")
                    continue
                if u == "N":
                    return "NEW_RULES"

                apply_command(board, game, parse_command(raw))

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
