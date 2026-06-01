# qminesweeper/__init__.py
import importlib.metadata

try:
    __version__ = importlib.metadata.version("qminesweeper")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0+dev"
