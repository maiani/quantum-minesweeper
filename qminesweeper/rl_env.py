# qminesweeper/rl_env.py
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import (
    GameConfig,
    GameStatus,
    MoveSet,
    QMineSweeperGame,
    WinCondition,
)


class QuantumMinesweeperEnv(gym.Env):
    """
    Gymnasium-compatible RL environment for Quantum Minesweeper.
    """

    metadata = {"render_modes": ["ansi"], "render_fps": 4}

    def __init__(self, rows=5, cols=5, mines=5, render_mode=None):
        super().__init__()

        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.render_mode = render_mode

        # --- Spaces ---
        # One action per cell (measure only for now)
        self.action_space = spaces.Discrete(rows * cols)

        # Observations: numeric board encoding from export_numeric_grid()
        self.observation_space = spaces.Box(low=-2.0, high=9.0, shape=(rows * cols,), dtype=np.float32)

        # --- Internal state ---
        self._game = None

    # ---------- RL API ----------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        # Init fresh board + game
        board = QMineSweeperBoard(rows=self.rows, cols=self.cols, backend=None)  # TODO: inject backend
        board.span_classical_mines(self.mines)  # simple setup
        cfg = GameConfig(win_condition=WinCondition.IDENTIFY, move_set=MoveSet.CLASSIC)
        self._game = QMineSweeperGame(board, cfg)

        obs = self._get_obs()
        return obs, {}

    def step(self, action):
        r = action // self.cols
        c = action % self.cols

        reward = 0.0
        terminated = False

        res = self._game.cmd_measure(r, c)

        # Reward shaping
        if res.skipped:
            reward = -0.1
        elif res.outcome == 1:  # mine hit
            reward = -1.0
            terminated = True
        else:  # safe cell
            reward = 0.5 * len(res.explored)  # encourage flood expansion

        if self._game.status == GameStatus.WIN:
            reward = 10.0
            terminated = True
        elif self._game.status == GameStatus.LOST:
            reward = -1.0
            terminated = True

        obs = self._get_obs()
        info = {}

        return obs, reward, terminated, False, info

    def render(self):
        if self.render_mode == "ansi":
            return str(self._game.board.export_numeric_grid())
        else:
            print(self._game.board.export_numeric_grid())

    # ---------- Helpers ----------
    def _get_obs(self):
        grid = self._game.board.export_numeric_grid()
        return grid.flatten().astype(np.float32)
