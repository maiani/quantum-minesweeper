from rich.console import Console
from rich.table import Table
from rich.text import Text
from quantum_board import QuantumBoard, init_classical_board, CellState, GameStatus, MoveType

console = Console()

def render_rich(qb: QuantumBoard, prec=1):
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column(" ", justify="right")  # row index label
    for col in range(1, qb.cols + 1):
        table.add_column(str(col), justify="center")

    for r in range(qb.rows):
        row = [str(r + 1)]
        for c in range(qb.cols):
            state = qb.cell_state[r, c]
            if state == CellState.UNEXPLORED:
                cell = Text("▢", style="dim")
            elif state == CellState.PINNED:
                cell = Text("⚑", style="yellow")
            elif state == CellState.EXPLORED:
                val = qb.get_clue(r, c)
                if val == 9:
                    cell = Text("💥", style="bold red")
                else:
                    cell = Text(f"{val:.{prec}f}", style="bold green")
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
    console.print("Select game type:\n1. Classical\n2. Quantum")
    while True:
        try:
            game_type = int(console.input("Enter [bold]1[/] or [bold]2[/]: ").strip())
            if game_type in (1, 2):
                break
        except ValueError:
            pass
        console.print("[red]Invalid input.[/]")

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

    return game_type, rows, cols, n_bombs

def game_loop_classical(rows, cols, n_bombs):
    qb = init_classical_board((rows, cols), n_bombs)
    render_rich(qb)
    console.print("Click a cell: e.g. [bold]3,4[/], [bold]P 3,4[/] to pin, [bold]X 2,2[/] to apply gate")

    command_map = {
        "M": MoveType.MEASURE,
        "P": MoveType.PIN_TOGGLE
    }

    while qb.game_status == GameStatus.ONGOING:
        try:
            cell = console.input("[yellow]Your move[/] ([M/P] row,col or q): ").strip()
            if cell.lower() in ("q", "quit", "exit"):
                console.print("[italic]Game exited.[/]")
                break

            # Parse move type and coordinates
            if cell[0].upper() in command_map:
                cmd_str, pos = cell[0].upper(), cell[1:].strip()
            else:
                cmd_str, pos = "M", cell  # default to MEASURE

            move_type = command_map.get(cmd_str, MoveType.MEASURE)
            r, c = map(int, pos.split(","))
            if not (1 <= r <= rows and 1 <= c <= cols):
                console.print("[red]Cell out of bounds.[/]")
                continue

            qb.move(move_type, (r - 1, c - 1))  # zero-based index
            render_rich(qb)
            console.print(f"[cyan]Game status:[/] [bold]{qb.game_status.name}[/]")

        except Exception as e:
            console.print(f"[red]Invalid input:[/] {e}")

    console.print("[bold]Game over![/bold]")

def game_loop_quantum(rows, cols, n_bombs):
    qb = init_classical_board((rows, cols), n_bombs)
    render_rich(qb)
    console.print("Click a cell: e.g. [bold]3,4[/], [bold]P 3,4[/] to pin, [bold]X 2,2[/] to apply gate")

    command_map = {
        "M": MoveType.MEASURE,
        "P": MoveType.PIN_TOGGLE,
        "X": MoveType.X_GATE,
        "Y": MoveType.Y_GATE,
        "Z": MoveType.Z_GATE,
        "H": MoveType.H_GATE,
        "S": MoveType.S_GATE,
    }

    while qb.game_status == GameStatus.ONGOING:
        try:
            cell = console.input("[yellow]Your move[/] ([M/P/X/Y/Z/H/S] row,col or q): ").strip()
            if cell.lower() in ("q", "quit", "exit"):
                console.print("[italic]Game exited.[/]")
                break

            # Parse move type and coordinates
            if cell[0].upper() in command_map:
                cmd_str, pos = cell[0].upper(), cell[1:].strip()
            else:
                cmd_str, pos = "M", cell  # default to MEASURE

            move_type = command_map.get(cmd_str, MoveType.MEASURE)
            r, c = map(int, pos.split(","))
            if not (1 <= r <= rows and 1 <= c <= cols):
                console.print("[red]Cell out of bounds.[/]")
                continue

            qb.move(move_type, (r - 1, c - 1))  # zero-based index
            render_rich(qb)
            console.print(f"[cyan]Game status:[/] [bold]{qb.game_status.name}[/]")

        except Exception as e:
            console.print(f"[red]Invalid input:[/] {e}")

    console.print("[bold]Game over![/bold]")

def main():
    welcome_screen()
    game_type, rows, cols, n_bombs = game_setup()

    if game_type == 1:
        game_loop_classical(rows, cols, n_bombs)
    elif game_type == 2:
        game_loop_quantum(rows, cols, n_bombs)
    else:
        console.print("[italic]Quantum mode not implemented yet.[/italic]")

if __name__ == "__main__":
    main()
