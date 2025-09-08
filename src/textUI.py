# ./src/textUI.py
from rich.console import Console
from rich.table import Table
from rich.text import Text

from quantum_board import QMineSweeperGame, GameStatus, MoveType, GameMode
from quantum_backend import QuantumBackend  # interface

console = Console()

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
        table.add_column(Text(str(col)), justify="center")

    grid = qb.export_grid()
    for r in range(qb.rows):
        row = [Text(str(r + 1))]  # add row label first
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

    console.print("Entanglement level:\n"
                  "  [cyan]0.[/] Classical bombs (|1⟩)\n"
                  "  [cyan]1.[/] Product stabilizers\n"
                  "  [cyan]2.[/] Entangled pairs\n"
                  "  [cyan]3.[/] 3-body stabilizers (etc.)")
    while True:
        try:
            ent_level = int(console.input("Enter level [0-3]: ").strip())
            if ent_level >= 0:
                break
        except ValueError:
            pass
        console.print("[red]Invalid input. Please enter a non-negative integer.[/]")

    return mode, rows, cols, n_bombs, ent_level


def make_board(backend : QuantumBackend, mode: GameMode, rows: int, cols: int, n_bombs: int, ent_level: int) -> QMineSweeperGame:
    qb = QMineSweeperGame(rows, cols, mode, backend=backend)
    if ent_level == 0:
        qb.span_classical_bombs(n_bombs)
    else:
        qb.span_random_stabilizer_bombs(nbombs=n_bombs, level=ent_level)
    return qb


# ---------- Single loop that also supports Reset/New ----------
def game_loop(backend: QuantumBackend, mode: GameMode, rows: int, cols: int, n_bombs: int, ent_level: int):

    qb = make_board(backend=backend, mode=mode, rows=rows, cols=cols, n_bombs=n_bombs, ent_level=ent_level)

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
            "CX": MoveType.CX_GATE,
            "CY": MoveType.CY_GATE,
            "CZ": MoveType.CZ_GATE,
            "SWAP": MoveType.SWAP_GATE,
        })

        while True:  # outer loop lets us reset/regenerate without leaving the function
            while qb.game_status == GameStatus.ONGOING:
                try:
                    raw = console.input(
                        "[yellow]Your move[/] "
                        "([M/P/X/Y/Z/H/S] row,col | CX/CY/CZ/SWAP r1,c1 r2,c2 | R | N | Q): "
                    ).strip()
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
                        return "NEW_RULES"

                    # parse command and args
                    parts = raw.split()
                    cmd = parts[0].upper()

                    print(cmd)

                    # two-qubit gates
                    if cmd in ("CX", "CY", "CZ", "SWAP"):
                        if len(parts) != 3:
                            console.print(f"[red]Format: {cmd} r1,c1 r2,c2[/]")
                            continue
                        try:
                            r1, c1 = map(int, parts[1].split(","))
                            r2, c2 = map(int, parts[2].split(","))
                        except ValueError:
                            console.print("[red]Invalid coordinates. Use row,col format.[/]")
                            continue
                        qb.move(cmd_map[cmd], (r1 - 1, c1 - 1), (r2 - 1, c2 - 1))

                    # one-qubit gates or measure/pin
                    else:
                        if cmd in cmd_map:
                            if len(parts) < 2:
                                console.print(f"[red]Format: {cmd} row,col[/]")
                                continue
                            pos = parts[1]
                        else:
                            cmd, pos = "M", raw  # default to measure
                        try:
                            r, c = map(int, pos.split(","))
                        except ValueError:
                            console.print("[red]Invalid coordinates. Use row,col format.[/]")
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
                    qb = make_board(
                        backend=backend, mode=mode, rows=rows,
                        cols=cols, n_bombs=n_bombs, ent_level=ent_level
                    )
                    render_rich(qb)
                    break  # back to inner gameplay loop
                elif choice == "R":
                    # reset to the same preparation circuit and let user explore again
                    qb.reset_board()
                    render_rich(qb)
                    break  # back to inner gameplay loop
                else:
                    console.print("[red]Please choose N, S, R, or Q.[/]")


def run_tui(backend: QuantumBackend):
    welcome_screen()
    while True:
        mode, rows, cols, n_bombs, ent_level = game_setup()
        outcome = game_loop(backend, mode, rows, cols, n_bombs, ent_level)
        if outcome == "QUIT":
            break
        if outcome == "NEW_RULES":
            # loop back to setup for new rules
            continue
