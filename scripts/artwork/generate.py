#!/usr/bin/env python
"""Generate the shared game mark, Pin-help flag, and installable app icons.

The functions in this file are the editable artwork source.  In particular,
``_bomb_mark`` defines the favicon mark once; the Pin-help flag and PWA icon
reuse exactly those elements with only a scale and translation.

Run ``pixi run icons`` after editing this file.  ``--check`` exits non-zero if
any tracked output has drifted from the generator.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.dom import minidom

import svg

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "qminesweeper" / "static"
FAVICON = STATIC / "favicon.svg"
PIN_FLAG = STATIC / "help" / "P-move" / "svgs" / "logo-flag.svg"
ICON_SVG = STATIC / "icons" / "icon.svg"
PNG_TARGETS = ((STATIC / "icons" / "icon-192.png", 192), (STATIC / "icons" / "icon-512.png", 512))

VIEWBOX = svg.ViewBoxSpec(0, 0, 64, 64)
BOMB_GRADIENT = "bomb-body"
CLOTH_GRADIENT = "flag-cloth"
FLAG_CLIP = "flag-clip"
FLAG_PATH = "M14 10.5c12-6 23 5 40-2v30c-17 7-28-4-40 2Z"
FLAG_COLOR = "#7891b3"
POLE_COLOR = "#526b8d"


def _bomb_gradient() -> svg.LinearGradient:
    """The original dark-blue logo tone, with restrained dimensionality."""
    return svg.LinearGradient(
        id=BOMB_GRADIENT,
        x1=12,
        y1=24,
        x2=43,
        y2=55,
        gradientUnits="userSpaceOnUse",
        elements=[
            svg.Stop(offset=0, stop_color="#324b6c"),
            svg.Stop(offset=1, stop_color="#19283d"),
        ],
    )


def _bomb_mark() -> list[svg.Element]:
    """Return the canonical favicon mark reused by every branded bomb."""
    return [
        svg.Circle(cx=27, cy=40, r=17.5, fill=f"url(#{BOMB_GRADIENT})"),
        # A dashed rear arc and solid front arc make the equator read as depth.
        svg.Path(
            d="M9.5 40a17.5 6 0 0 1 35 0",
            fill="none",
            stroke="#fff",
            stroke_opacity=0.28,
            stroke_width=1.25,
            stroke_dasharray=[2, 2.4],
        ),
        svg.Path(
            d="M9.5 40a17.5 6 0 0 0 35 0",
            fill="none",
            stroke="#fff",
            stroke_opacity=0.72,
            stroke_width=1.5,
        ),
        # The state vector supplies the Bloch-sphere cue without a busy meridian.
        svg.Path(
            d="M27 40 18.5 30.2m0 0 .5 3m-.5-3 2.9.9",
            fill="none",
            stroke="#fff",
            stroke_opacity=0.9,
            stroke_width=1.55,
            stroke_linecap="round",
            stroke_linejoin="round",
        ),
        # One compact curve keeps the fuse organic without becoming busy.
        svg.Path(
            d="M37.7 26.1c1.8-3.8 4.7-2.3 7-5.6",
            fill="none",
            stroke="#19283d",
            stroke_width=3,
            stroke_linecap="round",
        ),
        svg.Path(
            d="m45 12 1.45 3.55L50 17l-3.55 1.45L45 22l-1.45-3.55L40 17l3.55-1.45Z",
            fill="#ffc93c",
        ),
    ]


def _favicon() -> svg.SVG:
    return svg.SVG(
        width=64,
        height=64,
        viewBox=VIEWBOX,
        elements=[svg.Defs(elements=[_bomb_gradient()]), *_bomb_mark()],
    )


def _pin_flag() -> svg.SVG:
    cloth = svg.LinearGradient(
        id=CLOTH_GRADIENT,
        x1=14,
        y1=8,
        x2=55,
        y2=42,
        gradientUnits="userSpaceOnUse",
        elements=[
            svg.Stop(offset=0, stop_color=FLAG_COLOR, stop_opacity=0.2),
            svg.Stop(offset=1, stop_color=FLAG_COLOR, stop_opacity=0.05),
        ],
    )
    definitions = svg.Defs(
        elements=[
            cloth,
            _bomb_gradient(),
            svg.ClipPath(id=FLAG_CLIP, elements=[svg.Path(d=FLAG_PATH)]),
        ]
    )
    flag = svg.G(
        extra={"stroke-linecap": "round", "stroke-linejoin": "round"},
        elements=[
            svg.Path(d="M12.5 55V8", fill="none", stroke=POLE_COLOR, stroke_width=2.5),
            svg.Path(
                d=FLAG_PATH,
                fill=f"url(#{CLOTH_GRADIENT})",
                stroke=FLAG_COLOR,
                stroke_width=2.25,
            ),
            svg.Path(d="M7.5 56h10", fill="none", stroke=POLE_COLOR, stroke_width=2.5),
        ],
    )
    mark = svg.G(
        clip_path=f"url(#{FLAG_CLIP})",
        elements=[
            svg.G(
                transform=[svg.Translate(19, 9.8), svg.Scale(0.47)],
                elements=_bomb_mark(),
            )
        ],
    )
    return svg.SVG(
        viewBox=VIEWBOX,
        extra={"role": "img", "aria-labelledby": "title desc"},
        elements=[
            svg.Title(id="title", text="Quantum Minesweeper logo flag"),
            svg.Desc(id="desc", text="A slender board flag carrying the game's Bloch-sphere bomb."),
            definitions,
            flag,
            mark,
        ],
    )


def _pwa_icon() -> svg.SVG:
    """Place the canonical mark in the launcher-safe central 72 percent."""
    return svg.SVG(
        width=512,
        height=512,
        viewBox=VIEWBOX,
        elements=[
            svg.Defs(elements=[_bomb_gradient()]),
            svg.G(
                transform=[svg.Translate(8.96, 8.96), svg.Scale(0.72)],
                elements=_bomb_mark(),
            ),
        ],
    )


def _serialize(document: svg.SVG) -> str:
    """Serialize consistently while keeping generated SVG diffs readable."""
    rough = str(document)
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding=None)
    lines = [line for line in pretty.splitlines() if line.strip()]
    lines.insert(1, "<!-- GENERATED by scripts/artwork/generate.py. Do not edit by hand. -->")
    return "\n".join(lines) + "\n"


def _svg_outputs() -> dict[Path, str]:
    return {
        FAVICON: _serialize(_favicon()),
        PIN_FLAG: _serialize(_pin_flag()),
        ICON_SVG: _serialize(_pwa_icon()),
    }


def _rasterizer(src: Path, out: Path, size: int) -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("rsvg-convert"):
        commands.append(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", str(out), str(src)])
    if shutil.which("convert"):
        commands.append(
            ["convert", "-background", "none", "-density", "384", "-resize", f"{size}x{size}", str(src), str(out)]
        )
    if shutil.which("inkscape"):
        commands.append(
            ["inkscape", str(src), "-w", str(size), "-h", str(size), "--export-type=png", f"--export-filename={out}"]
        )
    return commands


def _rasterize(src: Path, out: Path, size: int) -> None:
    commands = _rasterizer(src, out, size)
    if not commands:
        raise SystemExit("No SVG rasterizer found (need rsvg-convert, convert, or inkscape).")
    for command in commands:
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, OSError):
            continue
        if out.exists() and out.stat().st_size:
            return
    raise SystemExit(f"All rasterizers failed for {out.name}; tried: {[command[0] for command in commands]}")


def _png_pixels(path: Path) -> bytes:
    """Return decoded pixels, ignoring nondeterministic PNG metadata."""
    converter = shutil.which("convert")
    if converter is None:
        return path.read_bytes()
    result = subprocess.run(
        [converter, str(path), "rgba:-"],
        check=True,
        capture_output=True,
    )
    return result.stdout


def _write() -> None:
    for path, content in _svg_outputs().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  generated {path.relative_to(ROOT)}")
    for path, size in PNG_TARGETS:
        _rasterize(ICON_SVG, path, size)
        print(f"  generated {path.relative_to(ROOT)} ({size}x{size})")


def _check() -> None:
    stale = [path for path, expected in _svg_outputs().items() if not path.exists() or path.read_text() != expected]
    with tempfile.TemporaryDirectory(prefix="qms-artwork-") as directory:
        temporary = Path(directory)
        source = temporary / "icon.svg"
        source.write_text(_svg_outputs()[ICON_SVG], encoding="utf-8")
        for tracked, size in PNG_TARGETS:
            rendered = temporary / tracked.name
            _rasterize(source, rendered, size)
            if not tracked.exists() or _png_pixels(tracked) != _png_pixels(rendered):
                stale.append(tracked)
    if stale:
        names = ", ".join(str(path.relative_to(ROOT)) for path in stale)
        raise SystemExit(f"Generated artwork is stale: {names}. Run `pixi run icons`.")
    print("Generated artwork is current.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify tracked outputs without changing them")
    args = parser.parse_args()
    _check() if args.check else _write()


if __name__ == "__main__":
    main()
