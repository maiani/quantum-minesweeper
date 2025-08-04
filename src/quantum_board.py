from enum import IntEnum
import random
import numpy as np
from backend import QuantumBackend
from qiskit_backend import QiskitBackend 

class CellState(IntEnum):
    UNEXPLORED = 0
    PINNED = 1
    EXPLORED = 2

class GameStatus(IntEnum):
    ONGOING = 0
    WIN = 1
    LOSE = 2

class MoveType(IntEnum):
    MEASURE = 0
    PIN_TOGGLE = 1
    X_GATE = 2
    Y_GATE = 3
    Z_GATE = 4
    H_GATE = 5
    S_GATE = 6

class GameMode(IntEnum):
    CLASSIC = 0
    QUANTUM_IDENTIFY = 1
    QUANTUM_CLEAR = 2


nbr_offsets = [(-1, -1), (-1, 0), (-1, 1),
               ( 0, -1),          ( 0, 1),
               ( 1, -1), ( 1, 0), ( 1, 1)]

class QuantumBoard:
    def __init__(self, rows : int, cols : int, win_condition : GameMode):
        self.rows = rows
        self.cols = cols
        self.n = rows * cols
        self.backend = QiskitBackend(self.n)

        self.cell_state = np.full((rows, cols), CellState.UNEXPLORED, dtype=np.int8)
        self.game_status = GameStatus.ONGOING

        if isinstance(win_condition, GameMode):
            self.win_condition = win_condition
        else:
            raise ValueError("Win condition unsupported")

    def index(self, row :int, col: int) -> int:
        return row * self.cols + col

    def coords(self, idx : int) -> tuple[int, int]:
        return divmod(idx, self.cols)

    def expectation_z(self, idx : int) -> float:
        return self.backend.expectation_z(idx)

    def board_expectations(self) -> np.ndarray:
        return np.array([[self.expectation_z(self.index(r, c))
                          for c in range(self.cols)]
                         for r in range(self.rows)])

    def neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        return [(r, c) for dr, dc in nbr_offsets
                if 0 <= (r := row + dr) < self.rows
                and 0 <= (c := col + dc) < self.cols]

    def get_clue(self, row: int, col: int) -> float:
        idx = self.index(row, col)
        if self.expectation_z(idx) == -1:
            return 9.0
        return sum((1 - self.expectation_z(self.index(r, c))) / 2
                   for r, c in self.neighbors(row, col))

    def measure(self, row: int, col: int):
        idx = self.index(row, col)
        if self.cell_state[row, col] == CellState.PINNED:
            return None
        self.cell_state[row, col] = CellState.EXPLORED
        return self.backend.measure(idx)

    def measure_connected(self, row: int, col: int):
        to_explore = [(row, col)]
        while to_explore:
            r, c = to_explore.pop()
            self.measure(r, c)
            clue = self.get_clue(r, c)
            if clue == 0.0:
                for dr, dc in nbr_offsets:
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < self.rows and 0 <= nc < self.cols and
                        self.cell_state[nr, nc] == CellState.UNEXPLORED):
                        to_explore.append((nr, nc))

    def check_game_status(self):
        """
        Check the game status based on the current board state and win condition.
        Updates self.game_status to WIN, LOSE, or ONGOING.
        """

        bombs = (1.0 - self.board_expectations()) / 2
        explored = (self.cell_state == CellState.EXPLORED)
        pinned = (self.cell_state == CellState.PINNED)

        tol = 1e-6
        p0 = (bombs <= tol)
        p1 = (bombs >= 1 - tol)

        if self.win_condition == GameMode.CLASSIC:
            if np.any(explored[bombs > tol]):
                self.game_status = GameStatus.LOSE
            elif np.allclose(bombs + explored, 1.0):
                self.game_status = GameStatus.WIN
            else:
                self.game_status = GameStatus.ONGOING

        elif self.win_condition == GameMode.QUANTUM_IDENTIFY:
            if np.any(explored[bombs > tol]):
                self.game_status = GameStatus.LOSE
            elif np.all(~explored[p1]) and np.all(explored[p0]):
                self.game_status = GameStatus.WIN
            else:
                self.game_status = GameStatus.ONGOING

        elif self.win_condition == GameMode.QUANTUM_CLEAR:
            if np.any(explored[bombs > tol]):
                self.game_status = GameStatus.LOSE
            elif np.all(bombs <= tol):
                self.game_status = GameStatus.WIN
            else:
                self.game_status = GameStatus.ONGOING

    def apply_gate(self, gate: str, targets):
        self.backend.apply_gate(gate, targets)

    def move(self, move_type: MoveType, coord_1, coord_2=None):
        r1, c1 = coord_1
        idx = self.index(r1, c1)

        if move_type == MoveType.MEASURE:
            self.measure_connected(r1, c1)

        elif move_type == MoveType.PIN_TOGGLE:
            if self.cell_state[r1, c1] == CellState.PINNED:
                self.cell_state[r1, c1] = CellState.UNEXPLORED
            elif self.cell_state[r1, c1] == CellState.UNEXPLORED:
                self.cell_state[r1, c1] = CellState.PINNED

        elif move_type in [
            MoveType.X_GATE, MoveType.Y_GATE, MoveType.Z_GATE,
            MoveType.H_GATE, MoveType.S_GATE
        ]:
            gate_map = {
                MoveType.X_GATE: "X",
                MoveType.Y_GATE: "Y",
                MoveType.Z_GATE: "Z",
                MoveType.H_GATE: "H",
                MoveType.S_GATE: "S",
            }

            # Apply the gate to the specified qubit
            self.apply_gate(gate_map[move_type], [idx])

            # A gate move is applied to an already explored cell, we change the cell state to unexplored
            self.cell_state[r1, c1] = CellState.UNEXPLORED

        else:
            raise ValueError(f"Unsupported move type: {move_type}")

        # After any move, we check the game status
        self.check_game_status()

    def span_classical_bombs(self, nbombs : int):
        """
        Randomly place nbombs on the board by applying X gates to the corresponding qubits.        
        """
        all_coords = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        bomb_coords = np.random.choice(len(all_coords), size=nbombs, replace=False)
        for i in bomb_coords:
            r, c = all_coords[i]
            self.apply_gate("X", [self.index(r, c)])

    def span_quantum_product_bombs(self, nbombs: int):
        """
        Randomly place `nbombs` quantum bombs in random single-qubit stabilizer states.
        Each bomb is initialized independently using Clifford gates applied to |0⟩.
        The states used are the 6 single-qubit stabilizer states:
        |0⟩, |1⟩, |+⟩, |–⟩, |+i⟩, |–i⟩.
        """
        if nbombs > self.n:
            raise ValueError("Too many bombs for board size")

        all_coords = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        bomb_coords = np.random.choice(len(all_coords), size=nbombs, replace=False)

        # Define gate sequences for the 6 single-qubit stabilizer states
        stabilizer_gates = [
            [],                          # |0⟩
            ["X"],                       # |1⟩
            ["H"],                       # |+⟩
            ["X", "H"],                  # |–⟩
            ["H", "S"],                  # |+i⟩
            ["X", "H", "S"],             # |–i⟩
        ]

        for i in bomb_coords:
            r, c = all_coords[i]
            idx = self.index(r, c)
            gate_seq = random.choice(stabilizer_gates)
            for gate in gate_seq:
                self.apply_gate(gate, [idx])