# qminesweeper/__main__.py
from __future__ import annotations

import os

import typer
import uvicorn

from qminesweeper.backends import make_backend, normalize_backend
from qminesweeper.logging_config import setup_logging
from qminesweeper.settings import get_settings
from qminesweeper.textUI import run_tui

# Initialize logging once (uvicorn still prints its own access logs)
setup_logging()

app = typer.Typer(help="Quantum Minesweeper CLI")


@app.command()
def tui(backend: str | None = typer.Option(None, help="Backend: purepy, stim, or qiskit")):
    """
    Run the Text User Interface (TUI).
    Uses settings.BACKEND by default; --backend overrides for this run.
    """
    settings = get_settings()
    chosen = (backend or settings.BACKEND).strip().lower()
    try:
        run_tui(make_backend(chosen))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def webui(
    host: str | None = typer.Option(None, help="Bind host (default: 0.0.0.0)"),
    port: int | None = typer.Option(None, help="Port (default: $PORT or 8080)"),
    reload: bool = typer.Option(False, help="Auto-reload (default: False)"),
    backend: str | None = typer.Option(None, help="Backend: purepy, stim, or qiskit (default: settings.BACKEND)"),
):
    """
    Run the FastAPI web interface.
    Reads defaults from environment (PORT) and settings; CLI options override for this run.
    """
    settings = get_settings()

    # Backend override
    if backend is not None:
        try:
            settings.BACKEND = normalize_backend(backend)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    # Host/port resolution
    host_final = host or "0.0.0.0"
    port_final = port or int(os.getenv("PORT", "8080"))

    uvicorn.run(
        "qminesweeper.webapp:app",
        host=host_final,
        port=port_final,
        reload=reload,
        reload_dirs=["qminesweeper"],
    )


if __name__ == "__main__":
    app()
