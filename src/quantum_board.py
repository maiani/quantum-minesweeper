# ./src/quantum_board.py
from __future__ import annotations
from enum import IntEnum
import random
import numpy as np

from quantum_backend import QuantumBackend, StabilizerQuantumState


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
    def __init__(self, rows: int, cols: int, win_condition: GameMode,
                 backend: QuantumBackend):
        self.rows = rows
        self.cols = cols
        self.n = rows * cols

        # Backend factory + runtime state
        self.backend: QuantumBackend = backend 
        self.state: StabilizerQuantumState = self.backend.generate_stabilizer_state(self.n)

        # Store the preparation recipe: list of (gate_name, [targets])
        self.preparation_circuit: list[tuple[str, list[int]]] = []

        self.cell_state = np.full((rows, cols), CellState.UNEXPLORED, dtype=np.int8)
        self.game_status = GameStatus.ONGOING

        if isinstance(win_condition, GameMode):
            self.win_condition = win_condition
        else:
            raise ValueError("Win condition unsupported")

    # ---------- utils ----------
    def index(self, row: int, col: int) -> int:
        return row * self.cols + col

    def coords(self, idx: int) -> tuple[int, int]:
        return divmod(idx, self.cols)

    def expectation_z(self, idx: int) -> float:
        return self.state.expectation_z(idx)

    def board_expectations(self) -> np.ndarray:
        return np.array([[self.expectation_z(self.index(r, c))
                          for c in range(self.cols)]
                         for r in range(self.rows)])

    def neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        return [(r, c) for dr, dc in nbr_offsets
                if 0 <= (r := row + dr) < self.rows
                and 0 <= (c := col + dc) < self.cols]

    # ---------- reset using stored prep circuit ----------
    def reset_board(self):
        """
        Reset quantum state to |0>^n, reset visible state, and replay the stored
        preparation circuit to rebuild the same board configuration deterministically.
        """
        self.state.reset()
        self.cell_state.fill(CellState.UNEXPLORED)
        self.game_status = GameStatus.ONGOING

        for gate, targets in self.preparation_circuit:
            self.state.apply_gate(gate, targets)

    # ---------- gameplay ----------
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
        return self.state.measure(idx)

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
        bombs = (1.0 - self.board_expectations()) / 2
        explored = (self.cell_state == CellState.EXPLORED)

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

    def apply_gate(self, gate: str, targets: list[int]):
        self.state.apply_gate(gate, targets)

    def move(self, move_type: IntEnum, coord_1, coord_2=None):
        r1, c1 = coord_1
        idx = self.index(r1, c1)

        if move_type == MoveType.MEASURE:
            self.measure_connected(r1, c1)

        elif move_type == MoveType.PIN_TOGGLE:
            if self.cell_state[r1, c1] == CellState.PINNED:
                self.cell_state[r1, c1] = CellState.UNEXPLORED
            elif self.cell_state[r1, c1] == CellState.UNEXPLORED:
                self.cell_state[r1, c1] = CellState.PINNED

        elif move_type in (MoveType.X_GATE, MoveType.Y_GATE, MoveType.Z_GATE,
                           MoveType.H_GATE, MoveType.S_GATE):
            gate_map = {
                MoveType.X_GATE: "X",
                MoveType.Y_GATE: "Y",
                MoveType.Z_GATE: "Z",
                MoveType.H_GATE: "H",
                MoveType.S_GATE: "S",
            }
            self.apply_gate(gate_map[move_type], [idx])
            self.cell_state[r1, c1] = CellState.UNEXPLORED
        else:
            raise ValueError(f"Unsupported move type: {move_type}")

        self.check_game_status()

    # ---------- spanners now *write* circuit then reset ----------
    def span_classical_bombs(self, nbombs: int):
        if nbombs > self.n:
            raise ValueError("Too many bombs for board size")

        chosen = np.random.choice(np.arange(self.n), size=nbombs, replace=False)
        circuit: list[tuple[str, list[int]]] = [("X", [int(i)]) for i in chosen]
        self.preparation_circuit = circuit
        self.reset_board()

    def span_quantum_product_bombs(self, nbombs: int):
        if nbombs > self.n:
            raise ValueError("Too many bombs for board size")

        stabilizer_gates = [
            [], ["X"], ["H"], ["X", "H"], ["H", "S"], ["X", "H", "S"]
        ]
        chosen = np.random.choice(np.arange(self.n), size=nbombs, replace=False)
        circuit: list[tuple[str, list[int]]] = []
        for i in chosen:
            for g in random.choice(stabilizer_gates):
                circuit.append((g, [int(i)]))
        self.preparation_circuit = circuit
        self.reset_board()
