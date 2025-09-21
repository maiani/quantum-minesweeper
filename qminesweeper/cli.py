# qminesweeper/cli.py
from logging_config import setup_logging

from __main__ import app as _typer_app


def main():
    """Console script entrypoint for the qminesweeper CLI."""
    setup_logging()
    _typer_app()
