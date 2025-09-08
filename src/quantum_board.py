# ./src/quantum_board.py
from __future__ import annotations
from enum import IntEnum
import random
import numpy as np
from typing import Dict, Tuple, List

from qiskit.quantum_info import random_clifford, Clifford

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
    # Non-quantum move
    PIN_TOGGLE = -1

    # Measurement
    MEASURE   = 0

    # Single-qubit Clifford
    X_GATE    = 1
    Y_GATE    = 2
    Z_GATE    = 3
    H_GATE    = 4
    S_GATE    = 5
    SDG_GATE  = 6
    SX_GATE   = 7
    SXDG_GATE = 8
    SY_GATE   = 9
    SYDG_GATE = 10

    # Two-qubit Clifford
    CX_GATE   = 11
    CY_GATE   = 12
    CZ_GATE   = 13
    SWAP_GATE = 14


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

        # Preparation recipe
        self.preparation_circuit: List[Tuple[str, List[int]]] = []

        # Exploration + status
        self.exploration_state = np.full((rows, cols), CellState.UNEXPLORED, dtype=np.int8)
        self.game_status = GameStatus.ONGOING

        # Clue basis
        self.clue_basis: str = "Z"

        # Expectation caches: per-basis dicts
        self._exp_cache: Dict[str, np.ndarray] = {
            "X": np.full((rows, cols), np.nan, dtype=float),
            "Y": np.full((rows, cols), np.nan, dtype=float),
            "Z": np.full((rows, cols), np.nan, dtype=float),
        }
        self._locked_Z: Dict[int, float] = {}

        if isinstance(win_condition, GameMode):
            self.win_condition = win_condition
        else:
            raise ValueError("Win condition unsupported")

    # ---------- utils ----------
    def index(self, row: int, col: int) -> int:
        return row * self.cols + col

    def coords(self, idx: int) -> tuple[int, int]:
        return divmod(idx, self.cols)

    def neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        return [(r, c) for dr, dc in nbr_offsets
                if 0 <= (r := row + dr) < self.rows
                and 0 <= (c := col + dc) < self.cols]

    # ---------- cache helpers ----------
    def _invalidate_cache_selectively(self, *, gate_targets: list[int] | None = None, measured: list[int] | None = None):
        gate_targets = gate_targets or []
        measured = measured or []

        for idx in gate_targets:
            r, c = self.coords(idx)
            if self.exploration_state[r, c] == CellState.EXPLORED:
                self._locked_Z.pop(idx, None)
                self._exp_cache["Z"][r, c] = np.nan

        for idx in measured:
            r, c = self.coords(idx)
            val = self.quantum_state.expectation_pauli(idx, "Z")
            self._locked_Z[idx] = val
            self._exp_cache["Z"][r, c] = val
            self._exp_cache["X"][r, c] = np.nan
            self._exp_cache["Y"][r, c] = np.nan

        for b in ("X", "Y", "Z"):
            self._exp_cache[b][:] = np.nan
            for idx, val in self._locked_Z.items():
                r, c = self.coords(idx)
                self._exp_cache["Z"][r, c] = val

    def _get_expectation(self, idx: int, basis: str | None = None) -> float:
        b = basis or self.clue_basis
        r, c = self.coords(idx)
        if not np.isnan(self._exp_cache[b][r, c]):
            return self._exp_cache[b][r, c]
        v = self.quantum_state.expectation_pauli(idx, b)
        self._exp_cache[b][r, c] = v
        return v

    # ---------- reset ----------
    def reset_board(self):
        self.quantum_state.reset()
        self.exploration_state.fill(CellState.UNEXPLORED)
        self.game_status = GameStatus.ONGOING
        for gate, targets in self.preparation_circuit:
            self.quantum_state.apply_gate(gate, targets)
        self._exp_cache = {b: np.full((self.rows, self.cols), np.nan, dtype=float) for b in ("X","Y","Z")}
        self._locked_Z.clear()

    # ---------- clue ----------
    def set_clue_basis(self, basis: str):
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Clue basis must be 'X','Y','Z'")
        self.clue_basis = basis

    def get_clue(self, row: int, col: int) -> float:
        idx = self.index(row, col)
        exp_self = self._get_expectation(idx, self.clue_basis)
        if exp_self == -1.0:
            return 9.0
        return sum((1 - self._get_expectation(self.index(nr, nc), self.clue_basis)) / 2.0
                   for nr, nc in self.neighbors(row, col))

    def board_expectations(self, basis: str | None = None) -> np.ndarray:
        b = basis or self.clue_basis
        vals = np.empty(self.n, dtype=float)
        for i in range(self.n):
            r, c = self.coords(i)
            if not np.isnan(self._exp_cache[b][r, c]):
                vals[i] = self._exp_cache[b][r, c]
            else:
                v = self.quantum_state.expectation_pauli(i, b)
                self._exp_cache[b][r, c] = v
                vals[i] = v
        return vals.reshape(self.rows, self.cols)

    # ---------- win/lose checks ----------
    def check_loss_on_measure(self, idx: int) -> bool:
        expZ = self._get_expectation(idx, "Z")
        bomb_prob = (1.0 - expZ) / 2.0
        if bomb_prob > 1e-6:
            self.game_status = GameStatus.LOSE
            return True
        return False

    def check_win_global(self):
        bombs = (1.0 - self.board_expectations("Z")) / 2.0
        explored = (self.exploration_state == CellState.EXPLORED)
        pinned = (self.exploration_state == CellState.PINNED)
        tol = 1e-6

        if self.win_condition == GameMode.CLASSIC:
            if np.allclose(bombs + explored, 1.0):
                self.game_status = GameStatus.WIN
            else:
                self.game_status = GameStatus.ONGOING
        elif self.win_condition == GameMode.QUANTUM_IDENTIFY:
            p0 = (bombs <= tol)
            p1 = (bombs >= 1 - tol)
            if np.all(pinned[p1]) and np.all(p1[pinned]) and np.all(explored[p0]):
                self.game_status = GameStatus.WIN
            else:
                self.game_status = GameStatus.ONGOING
        elif self.win_condition == GameMode.QUANTUM_CLEAR:
            if np.all(bombs <= tol):
                self.game_status = GameStatus.WIN
            else:
                self.game_status = GameStatus.ONGOING

    # ---------- gameplay ----------
    def measure(self, row: int, col: int):
        idx = self.index(row, col)
        if self.exploration_state[row, col] == CellState.PINNED:
            return None
        self.exploration_state[row, col] = CellState.EXPLORED
        outcome = self.quantum_state.measure(idx)
        self._invalidate_cache_selectively(measured=[idx])

        if not self.check_loss_on_measure(idx):
            self.check_win_global()
        return outcome

    def measure_connected(self, row: int, col: int):
        to_explore = [(row, col)]
        while to_explore:
            r, c = to_explore.pop()
            idx = self.index(r, c)
            self.measure(r, c)
            if self.game_status == GameStatus.LOSE:
                return
            clue = self.get_clue(r, c)
            if clue == 0.0:
                for dr, dc in nbr_offsets:
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < self.rows and 0 <= nc < self.cols and
                        self.exploration_state[nr, nc] == CellState.UNEXPLORED):
                        to_explore.append((nr, nc))

    def apply_gate(self, gate: str, targets: list[int]):
        self.quantum_state.apply_gate(gate, targets)
        self._invalidate_cache_selectively(gate_targets=targets)
        self.check_win_global()

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
            self.check_win_global()
        else:
            gate_map = {
                MoveType.X_GATE: "X",
                MoveType.Y_GATE: "Y",
                MoveType.Z_GATE: "Z",
                MoveType.H_GATE: "H",
                MoveType.S_GATE: "S",
                MoveType.SDG_GATE: "Sdg",
                MoveType.SX_GATE: "SX",
                MoveType.SXDG_GATE: "SXdg",
                MoveType.SY_GATE: "SY",
                MoveType.SYDG_GATE: "SYdg",
                MoveType.CX_GATE: "CX",
                MoveType.CY_GATE: "CY",
                MoveType.CZ_GATE: "CZ",
                MoveType.SWAP_GATE: "SWAP",
            }
            if MoveType(move_type) not in gate_map:
                raise ValueError(f"Unsupported move type: {move_type}")
            self.apply_gate(gate_map[MoveType(move_type)], [idx] if coord_2 is None else [idx, self.index(*coord_2)])
            self.exploration_state[r1, c1] = CellState.UNEXPLORED

    # ---------- spanners ----------
    def span_classical_bombs(self, nbombs: int):
        if nbombs > self.n:
            raise ValueError("Too many bombs for board size")
        chosen = np.random.choice(np.arange(self.n), size=nbombs, replace=False)
        circuit: List[Tuple[str, List[int]]] = [("X", [int(i)]) for i in chosen]
        self.preparation_circuit = circuit
        self.reset_board()

    def span_random_stabilizer_bombs(self, nbombs: int, level: int):
        """
        Place `nbombs` bombs in groups of size `level`.
        Each group is initialized in a uniformly random stabilizer state,
        excluding trivial states completely empty as |0...0>.
        """
        if nbombs > self.n:
            raise ValueError("Too many bombs for board size")

        indices = list(np.random.choice(self.n, size=nbombs, replace=False))
        circuit: list[tuple[str, list[int]]] = []

        while indices:
            group_size = min(level, len(indices))
            group = [indices.pop() for _ in range(group_size)]

            # Sample until we don't hit a trivial state
            while True:
                cl = random_clifford(group_size)
                # reject identity Clifford (|0…0>)
                if cl == Clifford(np.eye(2 * group_size, dtype=int)):
                    continue
                break

            qc = cl.to_circuit()
            # map Qiskit qubits -> our board indices
            q_to_idx = {q: group[i] for i, q in enumerate(qc.qubits)}

            for instr in qc.data:
                op = instr.operation
                qargs = instr.qubits

                name = op.name.upper()
                if name == "SDG":
                    name = "Sdg"

                targets = [q_to_idx[q] for q in qargs]
                circuit.append((name, targets))

        self.preparation_circuit = circuit
        self.reset_board()

    def export_grid(self) -> np.ndarray:
        grid = np.full((self.rows, self.cols), -1.0, dtype=float)
        for r in range(self.rows):
            for c in range(self.cols):
                state = self.exploration_state[r, c]
                if state == CellState.EXPLORED:
                    grid[r, c] = self.get_clue(r, c)
                elif state == CellState.PINNED:
                    grid[r, c] = -2.0
        return grid
