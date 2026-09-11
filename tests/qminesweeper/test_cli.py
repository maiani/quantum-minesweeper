from __future__ import annotations

import importlib

from typer.testing import CliRunner


def test_installed_script_target_is_importable():
    """Guard the ``qminesweeper = qminesweeper.cli:main`` entrypoint."""
    cli = importlib.import_module("qminesweeper.cli")

    assert callable(cli.main)


def test_cli_help_lists_commands():
    from qminesweeper.cli import app

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "tui" in result.stdout
    assert "webui" in result.stdout


def test_webui_backend_override_survives_uvicorn_reload(monkeypatch):
    from qminesweeper import cli

    called = {}
    monkeypatch.setenv("QMS_BACKEND", "chppy")
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: called.update(args=args, kwargs=kwargs))

    cli.webui(host=None, port=8123, reload=True, backend="stim")

    assert called["args"] == ("qminesweeper.server:app",)
    assert called["kwargs"]["reload_dirs"] == ["src/qminesweeper"]
    assert cli.get_settings().BACKEND == "stim"
