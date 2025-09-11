# qminesweeper/board.py
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple, Dict, Optional
import numpy as np
from math import isclose

from qiskit.quantum_info import random_clifford, Clifford

from qminesweeper.quantum_backend import QuantumBackend, StabilizerQuantumState

class CellState(IntEnum):
    UNEXPLORED = 0
    PINNED = 1
    EXPLORED = 2


NBR_OFFSETS = [(-1, -1), (-1, 0), (-1, 1),
               ( 0, -1),          ( 0, 1),
               ( 1, -1), ( 1, 0), ( 1, 1)]


@dataclass
class MeasureResult:
    idx: int
    outcome: Optional[int]          # None if skipped
    explored: List[Tuple[int, int]] # cells newly marked EXPLORED (includes the seed)
    flood_measures: List[Tuple[int, int, int]]  # (r,c,outcome) for flood-expanded cells
    skipped: bool = False


class QMineSweeperBoard:
    """
    Generic game mechanics & physics. No win/lose or policy.
    Owns:
      - geometry, neighbors
      - quantum state & caches
      - preparation circuit
      - exploration / pins
      - clue basis + clue math
      - flood-fill behavior
    """

    def __init__(self, rows: int, cols: int, backend: QuantumBackend, *, flood_fill: bool = True):
        self.rows = rows
        self.cols = cols
        self.n = rows * cols

        self.backend: QuantumBackend = backend
        self.state: StabilizerQuantumState = self.backend.generate_stabilizer_state(self.n)

        # exploration/pins
        self._exploration = np.full((rows, cols), CellState.UNEXPLORED, dtype=np.int8)

        # basis & flood-fill
        self._clue_basis: str = "Z"
        self._flood_fill: bool = flood_fill

        # caches (per basis index->value)
        self._exp_cache: Dict[str, Dict[int, float]] = {"X": {}, "Y": {}, "Z": {}}

        # record of measured outcomes (Z-basis measurements)
        self._measured: Dict[int, int] = {}

        # preparation recipe
        self._prep: List[Tuple[str, List[int]]] = []

    # ---------- geometry ----------
    def index(self, r: int, c: int) -> int:
        return r * self.cols + c

    def coords(self, idx: int) -> Tuple[int, int]:
        return divmod(idx, self.cols)

    def neighbors(self, r: int, c: int) -> List[Tuple[int, int]]:
        out = []
        for dr, dc in NBR_OFFSETS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                out.append((nr, nc))
        return out

    # ---------- config ----------
    def set_flood_fill(self, on: bool):
        self._flood_fill = bool(on)

    def set_clue_basis(self, basis: str):
        if basis not in ("X", "Y", "Z"):
            raise ValueError("basis must be one of 'X','Y','Z'")
        self._clue_basis = basis

    @property
    def clue_basis(self) -> str:
        return self._clue_basis

    def exploration_state(self) -> np.ndarray:
        # return a copy to protect internal state
        return self._exploration.copy()
    
    @property
    def preparation_circuit(self):
        # return a shallow copy to keep it read-only from the outside
        return list(self._prep)

    # ---------- preparation ----------
    def set_preparation(self, circuit: List[Tuple[str, List[int]]]) -> None:
        self._prep = circuit

    def reset(self):
        # reset physics
        self.state.reset()
        # (re)apply preparation circuit
        for gate, targets in self._prep:
            self.state.apply_gate(gate, targets)
        # reset caches & exploration
        self._exp_cache = {"X": {}, "Y": {}, "Z": {}}
        self._measured.clear()
        self._exploration.fill(CellState.UNEXPLORED)

    # Ready-made preparations (optional helpers)
    def span_classical_bombs(self, nbombs: int):
        if nbombs > self.n:
            raise ValueError("Too many bombs for board size")
        chosen = np.random.choice(np.arange(self.n), size=nbombs, replace=False)
        circuit: List[Tuple[str, List[int]]] = [("X", [int(i)]) for i in chosen]
        self.set_preparation(circuit)
        self.reset()

    def span_random_stabilizer_bombs(self, nbombs: int, level: int):
        if nbombs > self.n:
            raise ValueError("Too many bombs for board size")
        if random_clifford is None or Clifford is None:
            raise RuntimeError("Qiskit not available for random stabilizer preparation")

        indices = list(np.random.choice(self.n, size=nbombs, replace=False))
        circuit: List[Tuple[str, List[int]]] = []

        while indices:
            group_size = min(level, len(indices))
            group = [indices.pop() for _ in range(group_size)]

            # sample until not identity (|0...0>)
            while True:
                cl = random_clifford(group_size)
                if hasattr(Clifford, "__eq__"):
                    if cl == Clifford(np.eye(2 * group_size, dtype=int)):
                        continue
                break

            qc = cl.to_circuit()
            q_to_idx = {q: group[i] for i, q in enumerate(qc.qubits)}

            for instr in qc.data:
                op = instr.operation
                qargs = instr.qubits

                name = op.name.upper()
                if name == "SDG":
                    name = "Sdg"
                targets = [q_to_idx[q] for q in qargs]
                circuit.append((name, targets))

        self.set_preparation(circuit)
        self.reset()

    def _is_deterministic_zero(self, idx: int, tol: float = 1e-9) -> bool:
            # Deterministic Z=0 measurement if <Z> == +1
            return isclose(self.expectation(idx, "Z"), 1.0, rel_tol=0.0, abs_tol=tol)

    def _auto_reveal_zero_regions(self) -> None:
        """After a state change (gate/basis switch), reveal any leftover
        zero-clue pockets that are deterministically safe in Z.
        Uses measure_cell so flood-fill behaves consistently."""
        if not self._flood_fill:
            return
        changed = True
        while changed:
            changed = False
            for r in range(self.rows):
                for c in range(self.cols):
                    if self._exploration[r, c] != CellState.UNEXPLORED:
                        continue
                    idx = self.index(r, c)
                    if self._is_deterministic_zero(idx) and self.clue_value(r, c, self._clue_basis) == 0.0:
                        res = self.measure_cell(r, c)  # safe: deterministic 0
                        if not res.skipped:
                            changed = True

    # ---------- mechanics: expectations/clues ----------
    def _invalidate_all_caches(self):
        self._exp_cache = {"X": {}, "Y": {}, "Z": {}}

    def expectation(self, idx: int, basis: str) -> float:
        cache = self._exp_cache[basis]
        if idx not in cache:
            cache[idx] = self.state.expectation_pauli(idx, basis)
        return cache[idx]

    def bomb_probability_z(self, idx: int) -> float:
        return (1.0 - self.expectation(idx, "Z")) / 2.0

    def clue_value(self, r: int, c: int, basis: Optional[str] = None) -> float:
        b = basis or self._clue_basis
        s = 0.0
        for (nr, nc) in self.neighbors(r, c):
            idx = self.index(nr, nc)
            s += (1.0 - self.expectation(idx, b)) / 2.0
        return s

    # Backward-compat clue accessor with sentinel 9.0 (💥) when self cell is definite bomb in basis
    def get_clue(self, r: int, c: int) -> float:
        idx = self.index(r, c)
        if self.expectation(idx, self._clue_basis) == -1.0:
            return 9.0
        return self.clue_value(r, c, self._clue_basis)

    def board_expectations(self, basis: str) -> np.ndarray:
        vals = np.empty(self.n, dtype=float)
        for i in range(self.n):
            vals[i] = self.expectation(i, basis)
        return vals.reshape(self.rows, self.cols)

    # ---------- mechanics: pins & measurement & gates ----------
    def toggle_pin(self, r: int, c: int) -> None:
        st = self._exploration[r, c]
        if st == CellState.PINNED:
            self._exploration[r, c] = CellState.UNEXPLORED
        elif st == CellState.UNEXPLORED:
            self._exploration[r, c] = CellState.PINNED
        # EXPLORED -> PIN not allowed (keep as-is)

    def apply_gate(self, gate: str, targets: List[Tuple[int, int]]) -> None:
        idxs = [self.index(r, c) for (r, c) in targets]
        self.state.apply_gate(gate, idxs)
        
        # un-explore any explored cells among targets (gates invalidate exploration)
        for (r, c) in targets:
            if self._exploration[r, c] == CellState.EXPLORED:
                self._exploration[r, c] = CellState.UNEXPLORED

        # Conservative invalidation (simple & safe)
        self._invalidate_all_caches()
        self._auto_reveal_zero_regions()

    def measure_cell(self, r: int, c: int) -> MeasureResult:
        """Measure (r,c) in Z and, if flood_fill=True and clue==0, expand."""
        idx = self.index(r, c)

        # skip if pinned or already explored
        if self._exploration[r, c] == CellState.PINNED or self._exploration[r, c] == CellState.EXPLORED:
            return MeasureResult(idx=idx, outcome=None, explored=[], flood_measures=[], skipped=True)

        # measure seed
        outcome = int(self.state.measure(idx))
        self._measured[idx] = outcome
        self._invalidate_all_caches()

        explored_cells = [(r, c)]
        self._exploration[r, c] = CellState.EXPLORED

        flood_measures: List[Tuple[int, int, int]] = []

        # flood-fill zero-clue regions
        if self._flood_fill:
            # Only expand from seed if its clue is zero (common Minesweeper behavior)
            if self.clue_value(r, c, self._clue_basis) == 0.0 and outcome == 0:
                stack = [(r, c)]
                visited = set([(r, c)])
                while stack:
                    rr, cc = stack.pop()
                    for nr, nc in self.neighbors(rr, cc):
                        if (nr, nc) in visited:
                            continue
                        visited.add((nr, nc))
                        if self._exploration[nr, nc] != CellState.UNEXPLORED:
                            continue
                        if self._exploration[nr, nc] == CellState.PINNED:
                            continue
                        # measure neighbor
                        nidx = self.index(nr, nc)
                        nout = int(self.state.measure(nidx))
                        self._measured[nidx] = nout
                        self._invalidate_all_caches()

                        self._exploration[nr, nc] = CellState.EXPLORED
                        explored_cells.append((nr, nc))
                        flood_measures.append((nr, nc, nout))

                        # keep expanding if neighbor clue is zero and outcome is 0
                        if nout == 0 and self.clue_value(nr, nc, self._clue_basis) == 0.0:
                            stack.append((nr, nc))

        return MeasureResult(idx=idx, outcome=outcome, explored=explored_cells, flood_measures=flood_measures, skipped=False)

    # ---------- numeric grid for UIs ----------
    def export_numeric_grid(self) -> np.ndarray:
        """-1 = unexplored, -2 = pinned, 9 = definite bomb at cell (basis),
           else fractional clue in current basis."""
        grid = np.full((self.rows, self.cols), -1.0, dtype=float)
        for r in range(self.rows):
            for c in range(self.cols):
                st = self._exploration[r, c]
                if st == CellState.UNEXPLORED:
                    grid[r, c] = -1.0
                elif st == CellState.PINNED:
                    grid[r, c] = -2.0
                else:
                    val = self.get_clue(r, c)
                    grid[r, c] = val
        return grid
