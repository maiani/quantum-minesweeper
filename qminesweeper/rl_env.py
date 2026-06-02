# qminesweeper/rl_env.py
from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from qminesweeper.backends import make_backend
from qminesweeper.engine import MOVE_SETS, WIN_CONDITIONS, Command, build_game
from qminesweeper.game import ALLOWED_MOVES, Action, GameStatus, MoveSet, WinCondition
from qminesweeper.quantum_backend import ONE_QUBIT_GATES, TWO_QUBIT_GATES, QuantumGate


class QuantumMinesweeperEnv(gym.Env):
    """Gymnasium-compatible RL environment for Quantum Minesweeper.

    The action space follows the configured ruleset, except pins are omitted
    because they are player annotations and carry no useful agent-side state
    change. Stim is the default backend for speed; pass ``backend="purepy"`` for
    no-native-dependency tests or browser-adjacent experiments.
    """

    metadata = {"render_modes": ["ansi"], "render_fps": 4}

    def __init__(
        self,
        rows: int = 5,
        cols: int = 5,
        mines: int = 5,
        ent_level: int = 0,
        win_condition: str | WinCondition = WinCondition.IDENTIFY,
        move_set: str | MoveSet = MoveSet.CLASSIC,
        backend: str = "stim",
        render_mode: str | None = None,
    ):
        super().__init__()

        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.ent_level = ent_level
        self.win_condition = self._coerce_win_condition(win_condition)
        self.move_set = self._coerce_move_set(move_set)
        self.backend = backend
        self.render_mode = render_mode

        self._actions = self._build_actions()
        self.action_space = spaces.Discrete(len(self._actions))
        self.observation_space = spaces.Box(low=-2.0, high=9.0, shape=(rows * cols,), dtype=np.float32)

        self._board = None
        self._game = None

    # ---------- RL API ----------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            # Board setup currently uses numpy's module-level RNG.
            np.random.seed(seed)

        self._board, self._game = build_game(
            make_backend(self.backend, default="stim"),
            self.rows,
            self.cols,
            self.mines,
            self.ent_level,
            self.win_condition,
            self.move_set,
        )
        return self._get_obs(), {"actions": self.action_meanings}

    def step(self, action):
        if self._game is None:
            raise RuntimeError("reset() must be called before step()")
        if not self.action_space.contains(action):
            raise ValueError(f"Action {action!r} is outside Discrete({self.action_space.n})")

        cmd = self._actions[int(action)]
        reward = -0.01 if cmd.kind == "gate" else 0.0

        try:
            if cmd.kind == "measure":
                res = self._game.cmd_measure(*cmd.cell)
                if res.skipped:
                    reward = -0.1
                elif res.outcome == 1:
                    reward = -1.0
                else:
                    reward = 0.5 * len(res.explored)
            elif cmd.kind == "gate":
                targets = [cmd.cell] if cmd.cell2 is None else [cmd.cell, cmd.cell2]
                self._game.cmd_gate(cmd.gate, targets)
            else:
                raise ValueError(f"Unsupported RL command kind: {cmd.kind}")
        except ValueError as exc:
            reward = -0.1
            info = {"command": self._command_label(cmd), "error": str(exc)}
        else:
            info = {"command": self._command_label(cmd)}

        if self._game.status == GameStatus.WIN:
            reward = 10.0
        elif self._game.status == GameStatus.LOST:
            reward = -1.0

        terminated = self._game.status in (GameStatus.WIN, GameStatus.LOST)
        return self._get_obs(), reward, terminated, False, info

    def render(self):
        if self._game is None:
            return "" if self.render_mode == "ansi" else None
        grid = self._game.board.export_numeric_grid()
        if self.render_mode == "ansi":
            return str(grid)
        print(grid)
        return None

    # ---------- Introspection ----------
    @property
    def action_meanings(self) -> list[str]:
        """Human-readable labels for the Discrete action ids."""
        return [self._command_label(cmd) for cmd in self._actions]

    # ---------- Helpers ----------
    def _get_obs(self):
        grid = self._game.board.export_numeric_grid()
        return grid.flatten().astype(np.float32)

    def _build_actions(self) -> list[Command]:
        allowed = ALLOWED_MOVES[self.move_set]
        actions: list[Command] = []

        cells = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        if Action.MEASURE in allowed:
            actions.extend(Command("measure", cell=cell) for cell in cells)

        gates = sorted((move for move in allowed if isinstance(move, QuantumGate)), key=lambda gate: gate.value)
        for gate in gates:
            if gate in ONE_QUBIT_GATES:
                actions.extend(Command("gate", gate=gate.value, cell=cell) for cell in cells)
            elif gate in TWO_QUBIT_GATES:
                actions.extend(
                    Command("gate", gate=gate.value, cell=control, cell2=target)
                    for control in cells
                    for target in cells
                    if target != control
                )

        if not actions:
            raise ValueError(f"Move set {self.move_set.name} exposes no RL actions")
        return actions

    @staticmethod
    def _coerce_win_condition(value: str | WinCondition) -> WinCondition:
        if isinstance(value, WinCondition):
            return value
        return WIN_CONDITIONS[value.lower()]

    @staticmethod
    def _coerce_move_set(value: str | MoveSet) -> MoveSet:
        if isinstance(value, MoveSet):
            return value
        return MOVE_SETS[value.lower()]

    @staticmethod
    def _command_label(cmd: Command) -> str:
        r, c = cmd.cell
        first = f"{r + 1},{c + 1}"
        if cmd.kind == "measure":
            return f"M {first}"
        if cmd.cell2 is None:
            return f"{cmd.gate} {first}"
        r2, c2 = cmd.cell2
        return f"{cmd.gate} {first} {r2 + 1},{c2 + 1}"
