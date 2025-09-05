# ./src/qms-tui.py
from rich.console import Console
from rich.table import Table
from rich.text import Text

from quantum_board import QMineSweeperGame, GameStatus, MoveType, GameMode
from qiskit_backend import QiskitBackend  # backend factory
from stim_backend import StimBackend  # alternative backend factory

console = Console()

# BACKEND = QiskitBackend()
BACKEND = StimBackend()


# ---------- Coloring helper for fractional clues ----------
def clue_style(val: float) -> str:
    v = min(max(val / 8.0, 0.0), 1.0)
    r = int(255 * v)
    g = int(255 * (1 - v))
    return f"rgb({r},{g},0)"


def render_rich(qb: QMineSweeperGame, prec: int = 1):
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column(" ", justify="right")  # row index label
    for col in range(1, qb.cols + 1):
        table.add_column(str(col), justify="center")

    grid = qb.export_grid()
    for r in range(qb.rows):
        row = [str(r + 1)]  # add row label first
        for c in range(qb.cols):
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
    console.print("[bold magenta]Quantum Minesweeper![/bold magenta]")


def game_setup():
    console.print("[bold]Select game type:[/]")
    console.print("  [cyan]1.[/] Classical")
    console.print("  [cyan]2.[/] Quantum Identify")
    console.print("  [cyan]3.[/] Quantum Clear")
    while True:
        try:
            choice = int(console.input("Enter choice [1-3]: ").strip())
            if choice in (1, 2, 3):
                break
        except ValueError:
            pass
        console.print("[red]Invalid input. Please enter 1, 2, or 3.[/]")

    mode = {1: GameMode.CLASSIC, 2: GameMode.QUANTUM_IDENTIFY, 3: GameMode.QUANTUM_CLEAR}[choice]

    while True:
        try:
            console.print("Enter board dimensions. Example: [bold]5,5[/]")
            dim = console.input("Rows,Cols: ").strip().split(",")
            rows, cols = map(int, dim)
            if rows > 0 and cols > 0:
                break
        except ValueError:
            pass
        console.print("[red]Please enter valid dimensions.[/]")

    while True:
        try:
            n_bombs = int(console.input("Bombs: "))
            if 0 < n_bombs < rows * cols:
                break
        except ValueError:
            pass
        console.print("[red]Enter a valid number of bombs.[/]")

    # Choose classical or quantum product bombs for spanning
    console.print("Bomb type:\n  [cyan]1.[/] Classical (|1⟩)\n  [cyan]2.[/] Quantum product stabilizers")
    while True:
        try:
            btype = int(console.input("Enter choice [1-2]: ").strip())
            if btype in (1, 2):
                break
        except ValueError:
            pass
        console.print("[red]Invalid input. Please enter 1 or 2.[/]")

    return mode, rows, cols, n_bombs, btype


def make_board(mode: GameMode, rows: int, cols: int, n_bombs: int, btype: int) -> QMineSweeperGame:
    qb = QMineSweeperGame(rows, cols, mode, backend=BACKEND)
    if btype == 1:
        qb.span_classical_bombs(n_bombs)
    else:
        qb.span_quantum_product_bombs(n_bombs)
    return qb


# ---------- Single loop that also supports Reset/New ----------
def game_loop(mode: GameMode, rows: int, cols: int, n_bombs: int, btype: int):
    def make_board():
        qb_ = QMineSweeperGame(rows, cols, mode, backend=BACKEND)
        if btype == 1:
            qb_.span_classical_bombs(n_bombs)
        else:
            qb_.span_quantum_product_bombs(n_bombs)
        return qb_

    qb = make_board()
    render_rich(qb)
    console.print(
        "Move examples: [bold]3,4[/] (measure), [bold]P 3,4[/] (pin), "
        "[bold]X 2,2[/] (gate), [bold]R[/] (reset board), [bold]N[/] (new game), [bold]Q[/] (quit)"
    )

    # enable gates only for quantum modes
    cmd_map = {"M": MoveType.MEASURE, "P": MoveType.PIN_TOGGLE}
    if mode in (GameMode.QUANTUM_IDENTIFY, GameMode.QUANTUM_CLEAR):
        cmd_map.update({
            "X": MoveType.X_GATE, "Y": MoveType.Y_GATE, "Z": MoveType.Z_GATE,
            "H": MoveType.H_GATE, "S": MoveType.S_GATE,
        })

    while True:  # outer loop lets us reset/regenerate without leaving the function
        while qb.game_status == GameStatus.ONGOING:
            try:
                raw = console.input("[yellow]Your move[/] ([M/P/X/Y/Z/H/S] row,col | R | N | Q): ").strip()
                if not raw:
                    continue

                # global commands
                if raw.upper() in ("Q", "QUIT", "EXIT"):
                    console.print("[italic]Game exited.[/]")
                    return "QUIT"

                if raw.upper() == "R":
                    qb.reset_board()
                    render_rich(qb)
                    console.print("[green]Board reset.[/]")
                    continue

                if raw.upper() == "N":
                    # end this run and go back to menu to pick new rules
                    return "NEW_RULES"

                # parse (cmd, r,c), default to MEASURE
                if raw[0].upper() in cmd_map:
                    cmd, pos = raw[0].upper(), raw[1:].strip()
                else:
                    cmd, pos = "M", raw

                r, c = map(int, pos.split(","))
                if not (1 <= r <= rows and 1 <= c <= cols):
                    console.print("[red]Cell out of bounds.[/]")
                    continue

                qb.move(cmd_map[cmd], (r - 1, c - 1))
                render_rich(qb)
                console.print(f"[cyan]Game status:[/] [bold]{qb.game_status.name}[/]")

            except Exception as e:
                console.print(f"[red]Invalid input:[/] {e}")

        # game over: offer post-game options
        console.print("[bold]Game over![/bold]")
        console.print(
            "Choose: [bold]N[/] new game (new rules) · [bold]S[/] new game (same rules) · "
            "[bold]R[/] reset board · [bold]Q[/] quit"
        )
        while True:
            choice = console.input("[yellow]Post-game[/] (N/S/R/Q): ").strip().upper()
            if choice == "Q":
                return "QUIT"
            elif choice == "N":
                return "NEW_RULES"
            elif choice == "S":
                # regenerate with the same rules & fresh bombs
                qb = make_board()
                render_rich(qb)
                break  # back to inner gameplay loop
            elif choice == "R":
                # reset to the same preparation circuit and let user explore again
                qb.reset_board()
                render_rich(qb)
                break  # back to inner gameplay loop
            else:
                console.print("[red]Please choose N, S, R, or Q.[/]")


def main():
    welcome_screen()
    while True:
        mode, rows, cols, n_bombs, btype = game_setup()
        outcome = game_loop(mode, rows, cols, n_bombs, btype)
        if outcome == "QUIT":
            break
        if outcome == "NEW_RULES":
            # loop back to setup for new rules
            continue


if __name__ == "__main__":
    main()
