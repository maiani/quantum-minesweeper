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


class QMineSweeperGame:
    def __init__(self, 
                 rows: int, 
                 cols: int, 
                 win_condition: GameMode,
                 backend: QuantumBackend):

        self.rows = rows
        self.cols = cols
        self.n = rows * cols

        # Backend factory + runtime state
        self.backend: QuantumBackend = backend 
        self.quantum_state: StabilizerQuantumState = self.backend.generate_stabilizer_state(self.n)

        # Store the preparation recipe: list of (gate_name, [targets])
        self.preparation_circuit: list[tuple[str, list[int]]] = []

        # Exploration status
        self.exploration_state = np.full((rows, cols), CellState.UNEXPLORED, dtype=np.int8)
        self.game_status = GameStatus.ONGOING

        # Cached clues (basis-dependent)
        self.clues = np.full((rows, cols), np.nan, dtype=float)
        self.clue_basis: str = "Z"   # default clue basis

        # Win condition
        if isinstance(win_condition, GameMode):
            self.win_condition = win_condition
        else:
            raise ValueError("Win condition unsupported")
        

    # ---------- utils ----------
    def index(self, row: int, col: int) -> int:
        return row * self.cols + col

    def coords(self, idx: int) -> tuple[int, int]:
        return divmod(idx, self.cols)

    def expectation(self, idx: int, basis: str | None = None) -> float:
        """
        Return ⟨basis⟩ for a single qubit at index.
        basis ∈ {"X","Y","Z"} (defaults to current clue_basis).
        """
        b = basis or self.clue_basis
        return self.quantum_state.expectation_pauli(idx, b)

    def board_expectations(self, basis: str | None = None) -> np.ndarray:
        """Return ⟨basis⟩ values for all qubits as 2D array."""
        b = basis or self.clue_basis
        vals = np.array([self.expectation(i, b) for i in range(self.n)])
        return vals.reshape(self.rows, self.cols)

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
        self.quantum_state.reset()
        self.exploration_state.fill(CellState.UNEXPLORED)
        self.game_status = GameStatus.ONGOING

        for gate, targets in self.preparation_circuit:
            self.quantum_state.apply_gate(gate, targets)

        self.update_clues()

    # ---------- clues / caching ----------
    def update_clues(self):
        """Recompute ⟨basis⟩ and cache all clue values for current clue_basis."""
        expectations = self.board_expectations(self.clue_basis)

        self.clues.fill(np.nan)
        for r in range(self.rows):
            for c in range(self.cols):
                if expectations[r, c] == -1:  # definite bomb
                    self.clues[r, c] = 9.0
                else:
                    total = 0.0
                    for nr, nc in self.neighbors(r, c):
                        total += (1 - expectations[nr, nc]) / 2
                    self.clues[r, c] = total

    def set_clue_basis(self, basis: str):
        """Switch clue basis ∈ {"X","Y","Z"} and recompute clues."""
        if basis not in ("X","Y","Z"):
            raise ValueError("Clue basis must be 'X','Y','Z'")
        self.clue_basis = basis
        self.update_clues()

    def get_clue(self, row: int, col: int) -> float:
        return self.clues[row, col]

    # ---------- gameplay ----------
    def measure(self, row: int, col: int):
        idx = self.index(row, col)
        if self.exploration_state[row, col] == CellState.PINNED:
            return None
        self.exploration_state[row, col] = CellState.EXPLORED
        outcome = self.quantum_state.measure(idx)
        self.update_clues()
        return outcome

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
                        self.exploration_state[nr, nc] == CellState.UNEXPLORED):
                        to_explore.append((nr, nc))

    def check_game_status(self):
        bombs = (1.0 - self.board_expectations("Z")) / 2  # WIN/LOSE always judged in Z-basis
        explored = (self.exploration_state == CellState.EXPLORED)

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
        self.quantum_state.apply_gate(gate, targets)
        self.update_clues()

    def move(self, move_type: IntEnum, coord_1, coord_2=None):
        r1, c1 = coord_1
        idx = self.index(r1, c1)

        if move_type == MoveType.MEASURE:
            self.measure_connected(r1, c1)

        elif move_type == MoveType.PIN_TOGGLE:
            if self.exploration_state[r1, c1] == CellState.PINNED:
                self.exploration_state[r1, c1] = CellState.UNEXPLORED
            elif self.exploration_state[r1, c1] == CellState.UNEXPLORED:
                self.exploration_state[r1, c1] = CellState.PINNED

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
            self.exploration_state[r1, c1] = CellState.UNEXPLORED
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

    def export_grid(self) -> np.ndarray:
        """
        Return a 2D numpy array encoding the visible board state:
        -1 = unexplored
        -2 = pinned
         9 = bomb (explored and bomb found)
         0..8 = clue values (floats allowed in quantum mode)
        """
        grid = np.full((self.rows, self.cols), -1.0, dtype=float)

        for r in range(self.rows):
            for c in range(self.cols):
                state = self.exploration_state[r, c]
                if state == CellState.EXPLORED:
                    grid[r, c] = self.get_clue(r, c)
                elif state == CellState.PINNED:
                    grid[r, c] = -2.0
        return grid
