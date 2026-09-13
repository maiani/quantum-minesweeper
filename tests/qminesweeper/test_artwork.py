"""Checks for the generated visual identity assets."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_generated_artwork_is_current() -> None:
    root = Path(__file__).resolve().parents[2]
    subprocess.run(
        [sys.executable, "scripts/artwork/generate.py", "--check"],
        cwd=root,
        check=True,
    )
