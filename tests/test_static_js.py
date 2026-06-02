"""Lightweight checks for framework-free static JavaScript."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC_SCRIPTS = ROOT / "qminesweeper" / "static" / "scripts"


@pytest.mark.parametrize("script", sorted(STATIC_SCRIPTS.glob("*.js")))
def test_static_script_has_valid_javascript_syntax(script: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; static JavaScript syntax check skipped")

    result = subprocess.run(
        [node, "--check", str(script)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
