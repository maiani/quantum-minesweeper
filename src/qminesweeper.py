#! /usr/bin/env python3
# ./src/qminesweeper.py

import typer
from textUI import run_tui
from qiskit_backend import QiskitBackend  # backend factory
from stim_backend import StimBackend  # alternative backend factory

cli = typer.Typer(add_completion=False)

@cli.command()
def tui(
    backend: str = typer.Option("stim", help="Backend to use: stim or qiskit"),
):
    """
    Run Quantum Minesweeper in the terminal (TUI).
    """
    if backend.lower() == "stim":
        be = StimBackend()
    elif backend.lower() == "qiskit":
        be = QiskitBackend()
    else:
        raise typer.BadParameter("Backend must be 'stim' or 'qiskit'.")

    run_tui(be)
    

if __name__ == "__main__":
    cli()
