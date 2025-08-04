from rich.console import Console
from rich.table import Table
from rich.text import Text
from quantum_board import QuantumBoard, CellState, GameStatus, MoveType, GameMode

console = Console()

def clue_style(val: float) -> str:
    """
    Return a color string for Rich based on clue value.
    Maps 0 → green, 8 → red, interpolates linearly.
    """
    # Normalize to [0, 1]
    v = min(max(val / 8.0, 0.0), 1.0)
    # Interpolate RGB between green (0,255,0) and red (255,0,0)
    r = int(255 * v)
    g = int(255 * (1 - v))
    b = 0
    return f"rgb({r},{g},{b})"

def render_rich(qb: QuantumBoard):
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column(" ", justify="right")  # row index label
    for col in range(1, qb.cols + 1):
        table.add_column(str(col), justify="center")

    for r in range(qb.rows):
        row = [str(r + 1)]
        for c in range(qb.cols):
            state = qb.cell_state[r, c]
            if state == CellState.UNEXPLORED:
                cell = Text("■", style="dim")  # filled square
            elif state == CellState.PINNED:
                cell = Text("⚑", style="yellow")
            elif state == CellState.EXPLORED:
                val = qb.get_clue(r, c)
                if val == 9:
                    cell = Text("💥", style="bold red")
                elif val == 0:
                    cell = Text(" ", style="on black")
                else:
                    clue_color = clue_style(val)
                    cell = Text(f"{val:.1f}", style=clue_color)
            else:
                cell = Text("?", style="red")
            row.append(cell)
        table.add_row(*row)

    console.clear()
    console.print(table)

def welcome_screen():
    console.clear()
    console.print("[bold magenta]Quantum Minesweeper![/bold magenta]")

def game_setup():
    game_mode_map = {
        1: GameMode.CLASSIC,
        2: GameMode.QUANTUM_IDENTIFY,
        3: GameMode.QUANTUM_CLEAR,
    }

    console.print("[bold]Select game type:[/]")
    console.print("  [cyan]1.[/] Classical")
    console.print("  [cyan]2.[/] Quantum Identify")
    console.print("  [cyan]3.[/] Quantum Clear")

    while True:
        try:
            choice = int(console.input("Enter choice [1-3]: ").strip())
            if choice in game_mode_map:
                game_mode = game_mode_map[choice]
                break
        except ValueError:
            pass
        console.print("[red]Invalid input. Please enter 1, 2, or 3.[/]")

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

    return game_mode, rows, cols, n_bombs

def game_loop(rows: int, cols: int, n_bombs: int, mode: GameMode):
    qb = QuantumBoard(rows, cols, mode)
    qb.span_classical_bombs(n_bombs)
    render_rich(qb)

    # Build command map depending on mode
    command_map = {
        "M": MoveType.MEASURE,
        "P": MoveType.PIN_TOGGLE
    }

    if mode in (GameMode.QUANTUM_IDENTIFY, GameMode.QUANTUM_CLEAR):
        command_map.update({
            "X": MoveType.X_GATE,
            "Y": MoveType.Y_GATE,
            "Z": MoveType.Z_GATE,
            "H": MoveType.H_GATE,
            "S": MoveType.S_GATE,
        })

    console.print("Select a cell: e.g. [bold]3,4[/], [bold]P 3,4[/] to Pin" +
                  (", or gate name coords, e.g. [bold]X 2,2[/], to apply gate" if mode != GameMode.CLASSIC else ""))

    while qb.game_status == GameStatus.ONGOING:
        try:
            cell = console.input("[yellow]Your move[/] ([M/P/...], row,col or q): ").strip()
            if cell.lower() in ("q", "quit", "exit"):
                console.print("[italic]Game exited.[/]")
                break

            if cell[0].upper() in command_map:
                cmd_str, pos = cell[0].upper(), cell[1:].strip()
            else:
                cmd_str, pos = "M", cell  # default to MEASURE

            move_type = command_map.get(cmd_str, MoveType.MEASURE)
            r, c = map(int, pos.split(","))
            if not (1 <= r <= rows and 1 <= c <= cols):
                console.print("[red]Cell out of bounds.[/]")
                continue

            qb.move(move_type, (r - 1, c - 1))
            render_rich(qb)
            console.print(f"[cyan]Game status:[/] [bold]{qb.game_status.name}[/]")

        except Exception as e:
            console.print(f"[red]Invalid input:[/] {e}")

    console.print("[bold]Game over![/bold]")


def main():
    welcome_screen()
    game_mode, rows, cols, n_bombs = game_setup()
    game_loop(rows, cols, n_bombs, game_mode)

if __name__ == "__main__":
    main()
