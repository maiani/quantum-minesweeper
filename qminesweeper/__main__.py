# qminesweeper/__main__.py
import typer
import uvicorn

from qminesweeper.textUI import run_tui
from qminesweeper.stim_backend import StimBackend
from qminesweeper.qiskit_backend import QiskitBackend


app = typer.Typer(help="Quantum Minesweeper CLI")

@app.command()
def tui(backend: str = typer.Option("stim", help="Backend: stim or qiskit")):
    """
    Run the Text User Interface (TUI).
    """
    if backend == "stim":
        run_tui(StimBackend())
    elif backend == "qiskit":
        run_tui(QiskitBackend())
    else:
        typer.echo("Invalid backend, choose 'stim' or 'qiskit'")


@app.command()
def webui(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,
):
    """
    Run the FastAPI web interface.
    """
    uvicorn.run(
        "qminesweeper.webapp:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
