# qminesweeper/cli.py
from __main__ import app as _typer_app
from qminesweeper.logging_config import setup_logging


def main():
    """Console script entrypoint for the qminesweeper CLI."""
    setup_logging()
    _typer_app()
