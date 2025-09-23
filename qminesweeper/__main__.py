# qminesweeper/__main__.py
from __future__ import annotations

import os

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
    host: str | None = typer.Option(None, help="Bind host (default: 0.0.0.0)"),
    port: int | None = typer.Option(None, help="Port (default: $PORT or 8080)"),
    reload: bool = typer.Option(False, help="Auto-reload (default: False)"),
    backend: str | None = typer.Option(None, help="Backend: stim or qiskit (default: settings.BACKEND)"),
):
    """
    Run the FastAPI web interface.
    Reads defaults from environment (PORT) and settings; CLI options override for this run.
    """
    settings = get_settings()

    # Backend override
    if backend is not None:
        chosen = backend.strip().lower()
        if chosen not in {"stim", "qiskit"}:
            raise typer.BadParameter("Invalid backend, choose 'stim' or 'qiskit'")
        settings.BACKEND = chosen

    # Host/port resolution
    host_final = host or "0.0.0.0"
    port_final = port or int(os.getenv("PORT", "8080"))

    uvicorn.run(
        "qminesweeper.webapp:app",
        host=host_final,
        port=port_final,
        reload=reload,
    )


if __name__ == "__main__":
    app()
