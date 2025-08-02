# src/qms_TUI.py
from rich.console import Console
from rich.table import Table
from rich.text import Text
from quantum_board import QuantumBoard, init_classical_board

console = Console()

def render_rich(qb: QuantumBoard, prec=1):
    obs = qb.explored
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))

    table.add_column(" ", justify="right")  # row index label
    for col in range(1, qb.cols + 1):
        table.add_column(str(col), justify="center")

    for r in range(qb.rows):
        row = [str(r + 1)]  # row label
        for c in range(qb.cols):
            if not qb.explored[r, c]:
                cell = Text("▢", style="dim")
            else:
                val = qb.get_clue(r, c)
                if val == 9:
                    cell = Text("💥", style="bold red")
                else:
                    cell = Text(f"{val:.{prec}f}", style="bold green")
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
    console.print("Click a cell: e.g. [bold]3,4[/]")

    while qb.status not in ["WIN", "LOSE"]:
        try:
            cell = console.input("[yellow]Your move[/] (row,col or q): ").strip()
            if cell.lower() in ("q", "quit", "exit"):
                console.print("[italic]Game exited.[/]")
                break

            r, c = map(int, cell.split(","))
            if not (1 <= r <= rows and 1 <= c <= cols):
                console.print("[red]Cell out of bounds.[/]")
                continue
            r -= 1
            c -= 1

            qb.measure_connected(r, c)
            qb.check_game_status()
            render_rich(qb)
            console.print(f"[cyan]Game status:[/] [bold]{qb.status}[/]")

        except Exception as e:
            console.print(f"[red]Invalid input:[/] {e}")

    console.print("[bold]Game over![/bold]")

def main():
    welcome_screen()
    game_type, rows, cols, n_bombs = game_setup()

    if game_type == 1:
        game_loop_classical(rows, cols, n_bombs)
    else:
        console.print("[italic]Quantum mode not implemented yet.[/italic]")

if __name__ == "__main__":
    main()
