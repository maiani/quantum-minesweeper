# qminesweeper/__init__.py
import importlib.metadata

from .board import QMineSweeperBoard, CellState
from .game import (
    QMineSweeperGame, GameConfig, WinCondition, MoveSet, GameStatus, MoveType
)

__version__ = importlib.metadata.version("qminesweeper")
