#!/usr/bin/env python
"""Rasterise the PWA app icon (qminesweeper/static/icons/icon.svg) to the PNG
sizes an installable PWA / Play-Store TWA needs.

PWAs must advertise raster icons (Chrome's install criteria and the Play Store
require at least 192x192 and 512x512 PNGs; SVG-only icons are not enough). This
script regenerates them from the single SVG source so the icon is never hand-
edited per size. Run it whenever icon.svg changes:

    python scripts/make_icons.py

It shells out to whichever SVG rasteriser is installed (rsvg-convert, inkscape,
or ImageMagick's convert), so it works in CI and on a dev box without pinning a
Python SVG library.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "qminesweeper" / "static" / "icons"
SRC = ICONS / "icon.svg"

# (output filename, pixel size). 192 + 512 are the install-criteria minimums.
TARGETS = [
    ("icon-192.png", 192),
    ("icon-512.png", 512),
]


def _candidates(src: Path, out: Path, size: int) -> list[list[str]]:
    """Rasteriser command lines to try, in preference order. Each is attempted
    until one succeeds, so a tool that is installed-but-broken (e.g. a snap
    Inkscape with a glibc mismatch) doesn't block the others."""
    cmds = []
    if shutil.which("rsvg-convert"):
        cmds.append(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", str(out), str(src)])
    if shutil.which("convert"):
        # -background none keeps the SVG's own background; -density boosts quality.
        cmds.append(["convert", "-background", "none", "-density", "384",
                     "-resize", f"{size}x{size}", str(src), str(out)])
    if shutil.which("inkscape"):
        cmds.append(["inkscape", str(src), "-w", str(size), "-h", str(size),
                     "--export-type=png", f"--export-filename={out}"])
    return cmds


def _rasterise(src: Path, out: Path, size: int) -> None:
    """Render `src` SVG to a `size`x`size` PNG using the first tool that works."""
    cmds = _candidates(src, out, size)
    if not cmds:
        sys.exit("No SVG rasteriser found (need rsvg-convert, convert, or inkscape).")
    for cmd in cmds:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out.exists() and out.stat().st_size > 0:
                return
        except (subprocess.CalledProcessError, OSError):
            continue
    sys.exit(f"All rasterisers failed for {out.name}; tried: {[c[0] for c in cmds]}")


def main() -> None:
    if not SRC.exists():
        sys.exit(f"Missing icon source: {SRC}")
    for name, size in TARGETS:
        out = ICONS / name
        _rasterise(SRC, out, size)
        print(f"  {out.relative_to(ROOT)}  ({size}x{size})")
    print(f"Rasterised {len(TARGETS)} PNG icons from {SRC.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
