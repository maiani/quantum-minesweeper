#!/usr/bin/env python
"""Run Node's syntax checker over every frontend JavaScript source file."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "src" / "qminesweeper" / "static" / "scripts"


def main() -> None:
    files = sorted(SCRIPTS.glob("*.js"))
    if not files:
        raise SystemExit(f"No JavaScript files found under {SCRIPTS}")
    for path in files:
        subprocess.run(["node", "--check", str(path)], check=True)


if __name__ == "__main__":
    main()
