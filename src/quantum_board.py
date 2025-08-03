from enum import IntEnum
import numpy as np
from qiskit import QuantumCircuit, QiskitError
from qiskit.quantum_info import StabilizerState, Pauli, Clifford
from qiskit.circuit.library import HGate, SGate, CXGate, XGate


class CellState(IntEnum):
    UNEXPLORED = 0
    PINNED = 1
    EXPLORED = 2


class GameStatus(IntEnum):
    ONGOING = 0
    WIN = 1
    LOSE = 2


class WinCondition(IntEnum):
    CLASSIC = 0
    ZERO = 1


nbr_offsets = [(-1, -1), (-1, 0), (-1, 1),
               ( 0, -1),          ( 0, 1),
               ( 1, -1), ( 1, 0), ( 1, 1)]


class QuantumBoard:
    def __init__(self, rows, cols, win_condition):
        self.rows = rows
        self.cols = cols
        self.n = rows * cols

        self.qc = QuantumCircuit(self.n)
        self.state = StabilizerState(self.qc)

        self.cell_state = np.full((rows, cols), CellState.UNEXPLORED, dtype=np.int8)
        self.game_status = GameStatus.ONGOING

        if isinstance(win_condition, WinCondition):
            self.win_condition = win_condition
        else:
            raise ValueError("Win condition unsupported")

    def index(self, row, col):
        return row * self.cols + col

    def coords(self, idx):
        return divmod(idx, self.cols)

    def expectation_z(self, idx):
        label = 'I' * (self.n - idx - 1) + 'Z' + 'I' * idx
        return self.state.expectation_value(Pauli(label))

    def board_expectations(self):
        grid = np.zeros((self.rows, self.cols))
        for r in range(self.rows):
            for c in range(self.cols):
                grid[r, c] = self.expectation_z(self.index(r, c))
        return grid

    def neighbors(self, row, col):
        return [(r, c) for dr, dc in nbr_offsets
                if 0 <= (r := row + dr) < self.rows
                and 0 <= (c := col + dc) < self.cols]

    def get_clue(self, row, col):
        idx = self.index(row, col)
        if self.expectation_z(idx) == -1:
            return 9.0
        else:
            return sum((1 - self.expectation_z(self.index(r, c))) / 2 for r, c in self.neighbors(row, col))

    def measure(self, row, col):
        idx = self.index(row, col)
        if self.cell_state[row, col] == CellState.PINNED:
            return None
        else:
            self.cell_state[row, col] = CellState.EXPLORED
            outcome, self.state = self.state.measure([idx])
            return outcome

    def measure_connected(self, row, col):
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
        if self.win_condition == WinCondition.CLASSIC:
            bombs = (1.0 - self.board_expectations()) / 2
            explored = (self.cell_state == CellState.EXPLORED)
            if np.allclose(bombs + explored, 1.0):
                self.game_status = GameStatus.WIN
            elif np.max(bombs * explored) > 0.0:
                self.game_status = GameStatus.LOSE
            else:
                self.game_status = GameStatus.ONGOING

    def probe_move(self, row, col):
        outcome = self.measure(row, col)
        self.check_game_status()

    def apply_gate(self, gate, targets):
        try:
            cl = Clifford(gate)
        except QiskitError as err:
            raise ValueError(f"Gate not Clifford-compatible: {err}") from err

        if cl.num_qubits not in (1, 2):
            raise ValueError("Only 1- or 2-qubit Clifford gates are supported")
        if cl.num_qubits != len(targets):
            raise ValueError("Number of targets does not match gate arity")

        self.state = self.state.evolve(cl, targets)


# ___________________INIT FUNCTION_________________

def init_classical_board(dim, nbombs):
    qb = QuantumBoard(*dim, WinCondition.CLASSIC)
    rows, cols = dim
    all_coords = [(r, c) for r in range(rows) for c in range(cols)]
    bomb_coords = np.random.choice(len(all_coords), size=nbombs, replace=False)

    for i in bomb_coords:
        r, c = all_coords[i]
        qb.apply_gate(XGate(), [qb.index(r, c)])
    return qb
