# qminesweeper/board.py
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple, Dict, Optional
import numpy as np
import math

from qminesweeper.quantum_backend import QuantumBackend, StabilizerQuantumState


class CellState(IntEnum):
    """Exploration state of a cell."""
    UNEXPLORED = 0
    PINNED = 1
    EXPLORED = 2


# Offsets for 8-neighborhood (row, col)
NBR_OFFSETS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1),
]


@dataclass
class MeasureMoveResult:
    """
    Result of measure move.
    
    Attributes
    ----------
    idx : int
        Flat index of the measured cell.
    outcome : Optional[int]
        Measurement outcome (0/1). None if skipped.
    explored : List[Tuple[int,int]]
        Cells newly marked as EXPLORED (includes the seed).
    flood_measures : List[Tuple[int,int,int]]
        Flood-expanded measurements as (r, c, outcome).
    skipped : bool
        True if measurement was skipped due to PINNED/EXPLORED.
    """
    idx: int
    outcome: Optional[int]
    explored: List[Tuple[int, int]]
    flood_measures: List[Tuple[int, int, int]]
    skipped: bool = False


class QMineSweeperBoard:
    """
    Core quantum Minesweeper board mechanics.

    Responsibilities:
    - Grid geometry and neighbors.
    - Quantum state preparation & reset.
    - Exploration, pinning, and flood-fill behavior.
    - Clue calculation based on local expectations.
    - Measurement and gate application.
    - Entanglement/entropy diagnostics.
    """

    def __init__(self, rows: int, cols: int, backend: QuantumBackend, *, flood_fill: bool = True):
        self.rows = rows
        self.cols = cols
        self.n = rows * cols

        # Backend state object (e.g. stabilizer simulator)
        self.backend: QuantumBackend = backend
        self.state: StabilizerQuantumState = self.backend.generate_stabilizer_state(self.n)

        # Cell exploration / pin state
        self._exploration = np.full((rows, cols), CellState.UNEXPLORED, dtype=np.int8)

        # Gameplay parameters
        self._clue_basis: str = "Z"
        self._flood_fill: bool = flood_fill

        # Record of measured outcomes (Z-basis)
        self._measured: Dict[int, int] = {}

        # Preparation recipe (list of gates)
        self._prep: List[Tuple[str, List[int]]] = []

    # ---------- geometry ----------
    def index(self, r: int, c: int) -> int:
        """Convert (row, col) -> flat index."""
        return r * self.cols + c

    def coords(self, idx: int) -> Tuple[int, int]:
        """Convert flat index -> (row, col)."""
        return divmod(idx, self.cols)

    def neighbors(self, r: int, c: int) -> List[Tuple[int, int]]:
        """Return 8-neighborhood of (r, c), clipped to board bounds."""
        out = []
        for dr, dc in NBR_OFFSETS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                out.append((nr, nc))
        return out

    # ---------- config ----------
    def set_flood_fill(self, on: bool):
        """Enable/disable flood-fill expansion."""
        self._flood_fill = bool(on)

    def set_clue_basis(self, basis: str):
        """Set basis used for clues (must be X, Y, or Z)."""
        if basis not in ("X", "Y", "Z"):
            raise ValueError("basis must be one of 'X','Y','Z'")
        self._clue_basis = basis

    @property
    def clue_basis(self) -> str:
        return self._clue_basis

    def exploration_state(self) -> np.ndarray:
        """Return a copy of the current exploration grid."""
        return self._exploration.copy()

    # ---------- preparation ----------    
    @property
    def preparation_circuit(self):
        """Return the preparation circuit (read-only shallow copy)."""
        return list(self._prep)

    def set_preparation(self, circuit: List[Tuple[str, List[int]]]) -> None:
        """Define preparation circuit to be re-applied on reset()."""
        self._prep = circuit

    def reset(self):
        """Reset state and reapply preparation circuit."""
        self.state.reset()
        for gate, targets in self._prep:
            self.state.apply_gate(gate, targets)

        self._measured.clear()
        self._exploration.fill(CellState.UNEXPLORED)

    def span_classical_mines(self, nmines: int):
        """Prepare board with nmines placed as classical |1> states."""
        if nmines > self.n:
            raise ValueError("Too many mines for board size")
        chosen = np.random.choice(np.arange(self.n), size=nmines, replace=False)
        circuit = [("X", [int(i)]) for i in chosen]
        self.set_preparation(circuit)
        self.reset()

    def span_random_stabilizer_mines(self, nmines: int, level: int) -> None:
        """
        Prepare the board with random stabilizer “mine” groups.

        - Partition the chosen `nmines` distinct qubit indices into groups of size up to `level`.
        - For each group of size k, repeatedly sample a k-qubit Clifford circuit from the backend
        until the *decomposition touches every local wire* at least once.
        - Convert each gate’s local targets (0..k-1) to **global** board indices and append to a
        single preparation circuit.
        - Finally, set that circuit as the board’s preparation and `reset()` to apply it.

        This makes tests that inspect `board.preparation_circuit` (coverage) pass, and preserves a
        single source of truth for the prepared state.

        Parameters
        ----------
        nmines : int
            Number of distinct qubit indices to include in the stabilizer “mines”.
            Must be ≤ total number of qubits on the board.
        level : int
            Maximum group size (k) per sampled Clifford block (e.g., 1, 2, 3).

        Raises
        ------
        ValueError
            If `nmines` exceeds the number of qubits on the board.
        RuntimeError
            If the backend repeatedly returns a decomposition that fails to touch all k wires.
        """
        if nmines > self.n:
            raise ValueError("Too many mines for board size")

        # Choose distinct flat indices in [0, n)
        pool: list[int] = list(np.random.choice(self.n, size=nmines, replace=False))

        # We accumulate a single global preparation circuit here and apply once at the end.
        full_circuit: list[tuple[str, list[int]]] = []

        while pool:
            k = min(level, len(pool))
            # Pop k distinct global indices for this group
            group: list[int] = [int(pool.pop()) for _ in range(k)]

            # Re-sample until every local wire (0..k-1) appears in some gate's target list
            MAX_TRIES = 256
            for _ in range(MAX_TRIES):
                local_circ = self.backend.random_clifford_circuit(k)
                # Track which local wires (0..k-1) are referenced by any gate
                touched_local: set[int] = set()

                # Stash mapped gates in case this sample is valid
                mapped_ops: list[tuple[str, list[int]]] = []

                for gate, local_targets in local_circ:
                    # Record touches using local (0..k-1) indices
                    for t in local_targets:
                        touched_local.add(int(t))
                    # Map to global board indices
                    mapped_ops.append((gate, [group[t] for t in local_targets]))

                if len(touched_local) == k:
                    # Success: append to the global prep circuit and move to next group
                    full_circuit.extend(mapped_ops)
                    break
            else:
                # Exhausted retries without touching all wires — surface a clear error
                raise RuntimeError(
                    f"Failed to sample Clifford touching all {k} wires after {MAX_TRIES} attempts "
                    f"(group={group})."
                )

        # Commit the entire preparation in one shot; reset() applies it to self.state.
        self.set_preparation(full_circuit)
        self.reset()

    # ---------- mechanics: expectations/clues ----------
    def expectation(self, idx: int, basis: str) -> float:
        """Return <basis> expectation value for qubit idx."""
        return self.state.expectation_pauli(idx, basis)

    def mine_probability_z(self, idx: int) -> float:
        """Return probability that qubit idx is a mine (Z=1)."""
        return 0.5 * (1.0 - self.expectation(idx, "Z"))

    def clue_value(self, r: int, c: int, basis: Optional[str] = None) -> float:
        """
        Return clue for cell (r, c): sum of neighbor mine probabilities
        in the chosen basis.
        """
        b = basis or self._clue_basis
        return sum(0.5 * (1.0 - self.expectation(self.index(nr, nc), b))
                   for nr, nc in self.neighbors(r, c))

    def get_clue(self, r: int, c: int) -> float:
        """
        Return clue at (r, c) in current basis, or 9.0 if cell is a
        definite mine.
        """
        idx = self.index(r, c)
        if self.expectation(idx, self._clue_basis) == -1.0:
            return 9.0
        return self.clue_value(r, c, self._clue_basis)

    def board_expectations(self, basis: str) -> np.ndarray:
        """Return full board expectations in the given basis."""
        vals = np.array([self.expectation(i, basis) for i in range(self.n)], dtype=float)
        return vals.reshape(self.rows, self.cols)

    def expected_mines(self) -> float:
        """Return expected total number of mines (sum of Z-probs)."""
        return sum(self.mine_probability_z(i) for i in range(self.n))

    # ---------- mechanics: pins & measurement & gates ----------
    def toggle_pin(self, r: int, c: int) -> None:
        """Toggle pin on cell (r, c)."""
        st = self._exploration[r, c]
        if st == CellState.PINNED:
            self._exploration[r, c] = CellState.UNEXPLORED
        elif st == CellState.UNEXPLORED:
            self._exploration[r, c] = CellState.PINNED

    def apply_gate(self, gate: str, targets: List[Tuple[int, int]]) -> None:
        """Apply quantum gate to given cells (row,col)."""
        idxs = [self.index(r, c) for (r, c) in targets]
        self.state.apply_gate(gate, idxs)

        # Gates invalidate exploration
        for r, c in targets:
            if self._exploration[r, c] == CellState.EXPLORED:
                self._exploration[r, c] = CellState.UNEXPLORED

    def measure_cell(self, r: int, c: int) -> MeasureMoveResult:
        """
        Measure cell (r, c) in Z basis. If flood_fill=True and clue=0,
        expand to neighbors.
        """
        idx = self.index(r, c)

        # Skip if already explored/pinned
        if self._exploration[r, c] in (CellState.PINNED, CellState.EXPLORED):
            return MeasureMoveResult(idx=idx, outcome=None, explored=[], flood_measures=[], skipped=True)

        # Measure seed cell
        outcome = int(self.state.measure(idx))
        self._measured[idx] = outcome
        self._exploration[r, c] = CellState.EXPLORED

        explored_cells = [(r, c)]
        flood_measures: List[Tuple[int, int, int]] = []

        # Flood-fill expansion
        if self._flood_fill and outcome == 0 and self.clue_value(r, c, self._clue_basis) == 0.0:
            stack = [(r, c)]
            visited = {(r, c)}
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

                    nidx = self.index(nr, nc)
                    nout = int(self.state.measure(nidx))
                    self._measured[nidx] = nout
                    self._exploration[nr, nc] = CellState.EXPLORED

                    explored_cells.append((nr, nc))
                    flood_measures.append((nr, nc, nout))

                    if nout == 0 and self.clue_value(nr, nc, self._clue_basis) == 0.0:
                        stack.append((nr, nc))

        return MeasureMoveResult(idx=idx, outcome=outcome, explored=explored_cells, flood_measures=flood_measures)

    # ---------- entanglement & entropy ----------
    def _bloch_vector(self, idx: int) -> tuple[float, float, float]:
        """Return Bloch vector components (<X>,<Y>,<Z>) for qubit idx."""
        return (self.expectation(idx, "X"),
                self.expectation(idx, "Y"),
                self.expectation(idx, "Z"))

    def _bloch_length(self, idx: int) -> float:
        """Return Bloch vector length |r| for qubit idx."""
        Ex, Ey, Ez = self._bloch_vector(idx)
        return math.sqrt(Ex*Ex + Ey*Ey + Ez*Ez)

    @staticmethod
    def _H2(p: float) -> float:
        """Binary entropy H2(p) in bits, with 0 log 0 = 0 convention."""
        if p <= 0.0 or p >= 1.0:
            return 0.0
        return -(p*math.log2(p) + (1.0-p)*math.log2(1.0-p))

    def single_qubit_entropy(self, idx: int) -> float:
        """Single-qubit entanglement entropy (vs. rest of system)."""
        s = self._bloch_length(idx)
        p = 0.5 * (1.0 + s)
        return self._H2(p)

    def entropy_map(self) -> np.ndarray:
        """Return board of single-qubit entropies (bits)."""
        vals = np.array([self.single_qubit_entropy(i) for i in range(self.n)], dtype=float)
        return vals.reshape(self.rows, self.cols)

    def entanglement_score(self, agg: str = "mean") -> float:
        """Aggregate single-qubit entropy across board (mean/median/max)."""
        emap = self.entropy_map()
        if agg == "mean":
            return float(np.mean(emap))
        if agg == "median":
            return float(np.median(emap))
        if agg == "max":
            return float(np.max(emap))
        raise ValueError("agg must be one of: mean, median, max")

    # ---------- export for UI ----------
    def export_numeric_grid(self) -> np.ndarray:
        """
        Export board for UI rendering.
        
        Encoding:
        -1 = unexplored
        -2 = pinned
         9 = definite mine
         else = fractional clue value
        """
        grid = np.full((self.rows, self.cols), -1.0, dtype=float)
        for r in range(self.rows):
            for c in range(self.cols):
                st = self._exploration[r, c]
                if st == CellState.UNEXPLORED:
                    grid[r, c] = -1.0
                elif st == CellState.PINNED:
                    grid[r, c] = -2.0
                else:
                    grid[r, c] = self.get_clue(r, c)
        return grid
