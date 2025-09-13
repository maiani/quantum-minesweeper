# qminesweeper/game.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import List, Tuple
import numpy as np

from qminesweeper.board import QMineSweeperBoard, CellState, MeasureResult


class GameStatus(IntEnum):
    ONGOING = 0
    WIN = 1
    LOST = 2


class WinCondition(Enum):
    IDENTIFY = auto()  
    CLEAR = auto()

class MoveType(IntEnum):
    # Non-quantum
    PIN_TOGGLE = -1
    MEASURE = 0
    # 1-qubit
    X_GATE = 1; Y_GATE = 2; Z_GATE = 3; H_GATE = 4; S_GATE = 5; SDG_GATE = 6
    SX_GATE = 7; SXDG_GATE = 8; SY_GATE = 9; SYDG_GATE = 10
    # 2-qubit
    CX_GATE = 11; CY_GATE = 12; CZ_GATE = 13; SWAP_GATE = 14


class MoveSet(Enum):
    CLASSIC = auto()     # measure + pin
    ONE_QUBIT = auto()   # + single-qubit gates
    ONE_QUBIT_COMPLETE = auto()  # + single-qubit gates (all)
    TWO_QUBIT = auto()    


_GATE_FROM_MOVE = {
    MoveType.X_GATE: "X", MoveType.Y_GATE: "Y", MoveType.Z_GATE: "Z",
    MoveType.H_GATE: "H", MoveType.S_GATE: "S", MoveType.SDG_GATE: "Sdg",
    MoveType.SX_GATE: "SX", MoveType.SXDG_GATE: "SXdg",
    MoveType.SY_GATE: "SY", MoveType.SYDG_GATE: "SYdg",
    MoveType.CX_GATE: "CX", MoveType.CY_GATE: "CY", MoveType.CZ_GATE: "CZ", MoveType.SWAP_GATE: "SWAP",
}

_ALLOWED = {
    MoveSet.CLASSIC:  {MoveType.MEASURE, MoveType.PIN_TOGGLE},
    
    MoveSet.ONE_QUBIT:{MoveType.MEASURE, MoveType.PIN_TOGGLE,
                       MoveType.X_GATE, MoveType.Y_GATE, MoveType.Z_GATE,
                       MoveType.H_GATE, MoveType.S_GATE},
    
    MoveSet.ONE_QUBIT_COMPLETE:{MoveType.MEASURE, MoveType.PIN_TOGGLE,
                       MoveType.X_GATE, MoveType.Y_GATE, MoveType.Z_GATE,
                       MoveType.H_GATE, MoveType.S_GATE, MoveType.SDG_GATE,
                       MoveType.SX_GATE, MoveType.SXDG_GATE, MoveType.SY_GATE, MoveType.SYDG_GATE},
    
    MoveSet.TWO_QUBIT: set(MoveType),
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
    def _allowed(self, mt: MoveType) -> bool:
        return mt in _ALLOWED[self.cfg.move_set]

    # ---------- commands ----------
    def cmd_toggle_pin(self, r: int, c: int):
        if not self._allowed(MoveType.PIN_TOGGLE): raise ValueError("Pin not allowed in this MoveSet")
        self.board.toggle_pin(r, c)
        self._check_win()

    def cmd_measure(self, r: int, c: int) -> MeasureResult:
        if not self._allowed(MoveType.MEASURE): raise ValueError("Measure not allowed in this MoveSet")
        res = self.board.measure_cell(r, c)
        self._update_status_after_measure(res)
        return res

    def cmd_gate(self, gate: str, targets: List[Tuple[int, int]]):
        # infer MoveType from gate name
        mt = None
        for k, v in _GATE_FROM_MOVE.items():
            if v.upper() == gate.upper():
                mt = k
                break
        if mt is None:
            raise ValueError(f"Unsupported gate: {gate}")
        if not self._allowed(mt):
            raise ValueError(f"Move {gate} not allowed in {self.cfg.move_set.name}")
        self.board.apply_gate(_GATE_FROM_MOVE[mt], targets)
        self._check_win()

    # ---------- rules ----------
    def _update_status_after_measure(self, res: MeasureResult):
        # Loss rule (IDENTIFY/CLASSIC): lose if you measured a '1' anywhere in this action
        if self.cfg.win_condition == WinCondition.IDENTIFY and not res.skipped:
            if (res.outcome == 1) or any((o == 1) for (_, _, o) in res.flood_measures):
                self.status = GameStatus.LOST
                return
        self._check_win()

    def _check_win(self):
        if self.cfg.win_condition == WinCondition.CLEAR:
            probs = np.array([self.board.bomb_probability_z(i) for i in range(self.board.n)])
            self.status = GameStatus.WIN if np.all(probs <= 1e-6) else GameStatus.ONGOING
            return

        # IDENTIFY / CLASSIC: win when all safe cells are explored (pins optional)
        state = self.board.exploration_state()
        explored = (state == CellState.EXPLORED)

        probs = np.fromiter((self.board.bomb_probability_z(i) for i in range(self.board.n)), float)
        safe  = (probs <= 1e-6).reshape(self.board.rows, self.board.cols)

        self.status = GameStatus.WIN if np.all(explored[safe]) else GameStatus.ONGOING
