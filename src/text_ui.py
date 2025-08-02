# src/text_ui.py
"""
Quantum Board for Minesweeper-like Game
This module implements a quantum board for a Minesweeper-like game using Qiskit's stabilizer formalism.
It allows for qubit initialization, measurement, and application of quantum gates.
"""

import numpy as np
from quantum_board import QuantumBoard, init_classical_board
from qiskit import QuantumCircuit, QiskitError
from qiskit.quantum_info import Statevector
from qiskit.quantum_info import StabilizerState, Pauli, Clifford
from qiskit.circuit.library import HGate, SGate, CXGate
from qiskit.circuit.library import HGate, CXGate, XGate


def print_all_board_clues(qb : QuantumBoard):
    """Print a grid of clues for each cell."""
    grid = np.zeros((qb.rows, qb.cols))
    for r in range(qb.rows):
        for c in range(qb.cols):
            grid[r, c] = qb.get_clue(r, c)
    print(np.round(grid, 2))


def render_ascii(qb : QuantumBoard, prec=2):
    """
    Return a text board:
    '____'  unexplored
    'xXXx'  bomb
    x.xx  clue (rounded to `prec` decimals)
    """
    obs = qb.explored
    lines = []
    fmt = f"{{:.{prec}f}}"
    for r in range(qb.rows):
        row = []
        for c in range(qb.cols):
            if obs[r, c] == 0.0:
                row.append("____")
            else:
                val = qb.get_clue(r, c)
                if val == 9.0:
                    row.append("xXXx")
                else:
                    row.append(fmt.format(val))
        lines.append(" ".join(row))
    return "\n".join(lines)


################# MAIN #################


def welcome_screen():
    ws = """\
    Quantum Minesweeper!\
    """
    print(ws)


def game_setup():
    print("Select game type:")
    print("1. Classical")
    print("2. Quantum")
    while True:
        game_type = int(input("Enter 1 or 2: ").strip())
        if game_type in (1, 2):
            break
        print("Invalid input. Please enter 1 or 2.")

    while True:
        try:
            rows = int(input("Enter number of rows: "))
            cols = int(input("Enter number of columns: "))
            if rows > 0 and cols > 0:
                break
            else:
                print("Rows and columns must be positive integers.")
        except ValueError:
            print("Please enter valid integers for rows and columns.")

    while True:
        try:
            n_bombs = int(input("Enter number of bombs: "))
            if 0 < n_bombs < rows * cols:
                break
            else:
                print("Number of bombs must be positive and less than total cells.")
        except ValueError:
            print("Please enter a valid integer for bombs.")

    return game_type, rows, cols, n_bombs
    
def game_loop_classical(rows, cols, n_bombs):
    qb = init_classical_board((rows, cols), n_bombs)
    print()
    print(render_ascii(qb, prec=2))
    print("Input the cell you want to probe. E.g. 3, 4 ")
    while qb.status not in ["WIN", "LOSE"]:
        try:
            cell = input("Cell (row, col): ").strip()
            if cell.lower() in ("q", "quit", "exit"):
                print("Exiting game.")
                break
            r, c = map(int, cell.split(","))
            if not (1 <= r < rows + 1 and 1 <= c < cols + 1):
                print("Cell out of bounds.")
                continue
            r -= 1
            c -= 1
            qb.measure_connected(r, c)
            qb.check_game_status()
            print(render_ascii(qb, prec=2))
            print(f"Game status: {qb.status}")
            print()
        except Exception as e:
            print(f"Invalid input: {e}")
    print("Game over!")

def main():
    welcome_screen()
    game_type, rows, cols, n_bombs = game_setup()

    if game_type == 1:
        game_loop_classical(rows, cols, n_bombs)
    if game_type == 2:
        pass

if __name__  == "__main__":
    main()



