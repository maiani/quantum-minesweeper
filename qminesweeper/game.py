# qminesweeper/game.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum, auto

import numpy as np

from qminesweeper.board import CellState, MeasureMoveResult, QMineSweeperBoard
from qminesweeper.quantum_backend import QuantumGate


class GameStatus(IntEnum):
    ONGOING = 0
    WIN = 1
    LOST = 2


class WinCondition(Enum):
    IDENTIFY = auto()  # identify all mines (all safe cells explored)
    CLEAR = auto()  # clear all mines (prob=0 everywhere)
    SANDBOX = auto()  # no win condition


# Non-gate actions that are still "moves"
class Action(Enum):
    MEASURE = "M"
    PIN = "P"


class MoveSet(Enum):
    CLASSIC = auto()  # measure + pin
    ONE_QUBIT = auto()  # + single-qubit gates
    ONE_QUBIT_COMPLETE = auto()  # + single-qubit gates (all)
    TWO_QUBIT = auto()  # + two-qubit gates
    TWO_QUBIT_EXTENDED = ()  # + two-qubit + all 1-qubit


# Allowed moves: mix of Action and QuantumGate enums
ALLOWED_MOVES: dict[MoveSet, set[Action | QuantumGate]] = {
    MoveSet.CLASSIC: {Action.MEASURE, Action.PIN},
    MoveSet.ONE_QUBIT: {
        Action.MEASURE,
        Action.PIN,
        QuantumGate.X,
        QuantumGate.Y,
        QuantumGate.Z,
        QuantumGate.H,
        QuantumGate.S,
    },
    MoveSet.ONE_QUBIT_COMPLETE: {
        Action.MEASURE,
        Action.PIN,
        QuantumGate.X,
        QuantumGate.Y,
        QuantumGate.Z,
        QuantumGate.H,
        QuantumGate.S,
        QuantumGate.Sdg,
        QuantumGate.SXdg,
        QuantumGate.SY,
        QuantumGate.SYdg,
    },
    MoveSet.TWO_QUBIT: {
        Action.MEASURE,
        Action.PIN,
        QuantumGate.X,
        QuantumGate.Y,
        QuantumGate.Z,
        QuantumGate.H,
        QuantumGate.S,
        QuantumGate.CX,
        QuantumGate.CZ,
        QuantumGate.SWAP,
    },
    MoveSet.TWO_QUBIT_EXTENDED: {
        Action.MEASURE,
        Action.PIN,
        QuantumGate.X,
        QuantumGate.Y,
        QuantumGate.Z,
        QuantumGate.H,
        QuantumGate.S,
        QuantumGate.Sdg,
        QuantumGate.SXdg,
        QuantumGate.SY,
        QuantumGate.SYdg,
        QuantumGate.CX,
        QuantumGate.CY,
        QuantumGate.CZ,
        QuantumGate.SWAP,
    },
}


@dataclass
class GameConfig:
    win_condition: WinCondition
    move_set: MoveSet


class QMineSweeperGame:
    """
    Thin rules engine:
      - enforces allowed moves
      - computes win/lose from Board state + actions
      - exposes controller-friendly commands
    """

    def __init__(self, board: QMineSweeperBoard, config: GameConfig):
        self.board = board
        self.cfg = config
        self.status = GameStatus.ONGOING

    # ---------- permissions ----------
    def _allowed(self, move: Action | QuantumGate) -> bool:
        return move in ALLOWED_MOVES[self.cfg.move_set]

    # ---------- commands ----------
    def cmd_toggle_pin(self, r: int, c: int) -> None:
        """
        Toggles the pin status of the cell at the specified row and column.
        Args:
            r (int): The row index of the cell to toggle pin.
            c (int): The column index of the cell to toggle pin.
        Raises:
            ValueError: If pinning is not allowed in the current MoveSet.
        """

        if not self._allowed(Action.PIN):
            raise ValueError("Pin not allowed in this MoveSet")
        self.board.toggle_pin(r, c)
        self._check_win()

    def cmd_measure(self, r: int, c: int) -> MeasureMoveResult:
        """
        Measure cell (r,c) and return the result.

        Parameters
        ----------
        r : int
            Row index of the cell to measure.
        c : int
            Column index of the cell to measure.

        Returns
        -------
        MeasureResult
            The result of the measurement.
        """
        if not self._allowed(Action.MEASURE):
            raise ValueError("Measure not allowed in this MoveSet")
        res = self.board.measure_cell(r, c)
        self._update_status_after_measure(res)
        return res

    def cmd_gate(self, gate: str | QuantumGate, targets: list[tuple[int, int]]) -> None:
        """
        Apply a quantum gate to the specified targets.

        Parameters
        ----------
        gate : str | QuantumGate
            Gate name (e.g., "X", "H", "CX"). Case-insensitive if str.
        targets : list[tuple[int, int]]
            List of (row, col) targets.
        """
        # Normalize to QuantumGate
        if isinstance(gate, QuantumGate):
            gate_enum = gate
        else:
            try:
                gate_enum = QuantumGate[gate] if gate.isupper() else QuantumGate(gate.upper())
            except Exception:
                raise ValueError(f"Unsupported gate: {gate}")

        if not self._allowed(gate_enum):
            raise ValueError(f"Move {gate_enum.value} not allowed in {self.cfg.move_set.name}")

        # Board still takes canonical string names
        self.board.apply_gate(gate_enum.value, targets)
        self._check_win()

    # ---------- rules ----------
    def _update_status_after_measure(self, res: MeasureMoveResult) -> None:
        if self.cfg.win_condition == WinCondition.SANDBOX:
            return
        if res.outcome == 1:
            self.status = GameStatus.LOST
        else:
            self._check_win()

    def _check_win(self) -> None:
        if self.cfg.win_condition == WinCondition.CLEAR:
            probs = np.array([self.board.mine_probability_z(i) for i in range(self.board.n)])
            self.status = GameStatus.WIN if np.all(probs <= 1e-6) else GameStatus.ONGOING
            return

        if self.cfg.win_condition == WinCondition.IDENTIFY:
            state = self.board.exploration_state()
            explored = state == CellState.EXPLORED
            probs = np.fromiter((self.board.mine_probability_z(i) for i in range(self.board.n)), float)
            safe = (probs <= 1e-6).reshape(self.board.rows, self.board.cols)
            self.status = GameStatus.WIN if np.all(explored[safe]) else GameStatus.ONGOING
