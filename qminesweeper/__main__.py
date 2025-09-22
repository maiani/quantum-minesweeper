# qminesweeper/__main__.py
from __future__ import annotations

import typer
import uvicorn

from qminesweeper.logging_config import setup_logging
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.settings import get_settings
from qminesweeper.stim_backend import StimBackend
from qminesweeper.textUI import run_tui

# Initialize logging once (uvicorn still prints its own access logs)
setup_logging()

app = typer.Typer(help="Quantum Minesweeper CLI")


@app.command()
def tui(backend: str | None = typer.Option(None, help="Backend: stim or qiskit")):
    """
    Run the Text User Interface (TUI).
    Uses settings.BACKEND by default; --backend overrides for this run.
    """
    settings = get_settings()
    chosen = (backend or settings.BACKEND).strip().lower()

    if chosen == "stim":
        run_tui(StimBackend())
        return
    if chosen == "qiskit":
        run_tui(QiskitBackend())
        return

    raise typer.BadParameter("Invalid backend, choose 'stim' or 'qiskit'")


@app.command()
def webui(
    host: str | None = typer.Option(None, help="Bind host (default: settings.WEB_HOST)"),
    port: int | None = typer.Option(None, help="Port (default: settings.WEB_PORT)"),
    reload: bool = typer.Option(True, help="Auto-reload"),
    backend: str | None = typer.Option(None, help="Backend: stim or qiskit (default: settings.BACKEND)"),
):
    """
    Run the FastAPI web interface.
    Reads defaults from settings; CLI options override for this run.
    """
    settings = get_settings()

    # Apply CLI overrides in-place for this process
    if backend is not None:
        chosen = backend.strip().lower()
        if chosen not in {"stim", "qiskit"}:
            raise typer.BadParameter("Invalid backend, choose 'stim' or 'qiskit'")
        settings.BACKEND = chosen

    if host is not None:
        settings.WEB_HOST = host

    if port is not None:
        settings.WEB_PORT = port

    uvicorn.run(
        "qminesweeper.webapp:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        reload=reload,
    )


if __name__ == "__main__":
    app()
