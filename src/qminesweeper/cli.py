"""Command-line interface shared by the module and installed script entrypoints."""

from __future__ import annotations

import os

import typer
import uvicorn

from qminesweeper.backends import make_backend, normalize_backend
from qminesweeper.logging_config import setup_logging
from qminesweeper.settings import get_settings
from qminesweeper.textUI import run_tui

app = typer.Typer(help="Quantum Minesweeper CLI")


@app.command()
def tui(backend: str | None = typer.Option(None, help="Backend: chppy, stim, or qiskit")):
    """Run the Text User Interface (TUI).

    Uses settings.BACKEND by default; --backend overrides it for this run.
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
    backend: str | None = typer.Option(None, help="Backend: chppy, stim, or qiskit (default: settings.BACKEND)"),
):
    """Run the FastAPI web interface.

    Reads defaults from the environment and settings; CLI options override them
    for this run.
    """
    settings = get_settings()

    if backend is not None:
        try:
            settings.BACKEND = normalize_backend(backend)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    uvicorn.run(
        "qminesweeper.server:app",
        host=host or "0.0.0.0",
        port=port or int(os.getenv("PORT", "8080")),
        reload=reload,
        reload_dirs=["qminesweeper"],
    )


def main() -> None:
    """Run the package-owned Typer app from either CLI entrypoint."""
    setup_logging()
    app()
