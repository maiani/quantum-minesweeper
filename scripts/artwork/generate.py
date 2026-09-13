#!/usr/bin/env python
"""Generate the shared game mark, Pin-help flag, and mobile app icon set.

The functions in this file are the editable artwork source.  In particular,
``_bomb_mark`` defines the favicon mark once; the Pin-help flag, PWA icons, and
mobile-store assets reuse exactly those elements with only presentation layers.

Run ``pixi run icons`` after editing this file.  ``--check`` exits non-zero if
any tracked output has drifted from the generator.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.dom import minidom

import svg

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "qminesweeper" / "static"
FAVICON = STATIC / "favicon.svg"
PIN_FLAG = STATIC / "help" / "P-move" / "svgs" / "logo-flag.svg"
ICON_SVG = STATIC / "icons" / "icon.svg"
ICONS = STATIC / "icons"
MASKABLE_SVG = ICONS / "icon-maskable.svg"
MOBILE = ROOT / "artwork" / "mobile"
ANDROID = MOBILE / "android"
MOBILE_MASTER_SVG = MOBILE / "app-icon.svg"
ANDROID_FOREGROUND_SVG = ANDROID / "foreground.svg"
ANDROID_BACKGROUND_SVG = ANDROID / "background.svg"
ANDROID_MONOCHROME_SVG = ANDROID / "monochrome.svg"
MASK_PREVIEW_SVG = MOBILE / "mask-preview.svg"
RASTER_TARGETS = (
    (ICON_SVG, ICONS / "icon-192.png", 192, 192),
    (ICON_SVG, ICONS / "icon-512.png", 512, 512),
    (MASKABLE_SVG, ICONS / "icon-maskable-192.png", 192, 192),
    (MASKABLE_SVG, ICONS / "icon-maskable-512.png", 512, 512),
    (MOBILE_MASTER_SVG, MOBILE / "app-icon-1024.png", 1024, 1024),
    (MOBILE_MASTER_SVG, MOBILE / "play-store-icon-512.png", 512, 512),
    (MOBILE_MASTER_SVG, ICONS / "apple-touch-icon-180.png", 180, 180),
    (ANDROID_FOREGROUND_SVG, ANDROID / "foreground-432.png", 432, 432),
    (ANDROID_BACKGROUND_SVG, ANDROID / "background-432.png", 432, 432),
    (ANDROID_MONOCHROME_SVG, ANDROID / "monochrome-432.png", 432, 432),
    (MASK_PREVIEW_SVG, MOBILE / "mask-preview.png", 840, 280),
)

VIEWBOX = svg.ViewBoxSpec(0, 0, 64, 64)
ADAPTIVE_VIEWBOX = svg.ViewBoxSpec(0, 0, 108, 108)
PREVIEW_VIEWBOX = svg.ViewBoxSpec(0, 0, 420, 140)
BOMB_GRADIENT = "bomb-body"
CLOTH_GRADIENT = "flag-cloth"
FLAG_CLIP = "flag-clip"
FLAG_PATH = "M14 10.5c12-6 23 5 40-2v30c-17 7-28-4-40 2Z"
FLAG_COLOR = "#7891b3"
POLE_COLOR = "#526b8d"
ICON_BACKGROUND = "#a9bad0"
MONOCHROME = "#000"

# The regular icon can use more of an unmasked canvas. The safe placement keeps
# the complete mark inside Android's guaranteed 66/108 adaptive-icon zone.
REGULAR_MARK_TRANSFORM = [svg.Translate(4.63, 0.03), svg.Scale(0.92)]
SAFE_MARK_TRANSFORM = [svg.Translate(7.6, 3.5), svg.Scale(0.82)]
ADAPTIVE_MARK_TRANSFORM = [svg.Translate(10.86, 3.61), svg.Scale(1.45)]


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


def _monochrome_mark() -> list[svg.Element]:
    """A single-alpha-layer version for Android themed icons."""
    return [
        svg.Circle(cx=27, cy=40, r=16, fill="none", stroke=MONOCHROME, stroke_width=3),
        svg.Path(
            d="M11 40a16 5.5 0 0 1 32 0",
            fill="none",
            stroke=MONOCHROME,
            stroke_width=1.8,
            stroke_dasharray=[2.5, 2.5],
        ),
        svg.Path(
            d="M11 40a16 5.5 0 0 0 32 0",
            fill="none",
            stroke=MONOCHROME,
            stroke_width=2.2,
        ),
        svg.Path(
            d="M27 40 18.5 30.2m0 0 .5 3m-.5-3 2.9.9",
            fill="none",
            stroke=MONOCHROME,
            stroke_width=2,
            stroke_linecap="round",
            stroke_linejoin="round",
        ),
        svg.Path(
            d="M37.7 26.1c1.8-3.8 4.7-2.3 7-5.6",
            fill="none",
            stroke=MONOCHROME,
            stroke_width=3,
            stroke_linecap="round",
        ),
        svg.Path(
            d="m45 12 1.45 3.55L50 17l-3.55 1.45L45 22l-1.45-3.55L40 17l3.55-1.45Z",
            fill=MONOCHROME,
        ),
    ]


def _icon_layers(transform: list[svg.Transform]) -> list[svg.Element]:
    return [
        svg.Rect(width=64, height=64, fill=ICON_BACKGROUND),
        svg.G(transform=transform, elements=_bomb_mark()),
    ]


def _app_icon(*, mask_safe: bool) -> svg.SVG:
    """Create an opaque square icon; platform masks provide the outer shape."""
    transform = SAFE_MARK_TRANSFORM if mask_safe else REGULAR_MARK_TRANSFORM
    return svg.SVG(
        width=512,
        height=512,
        viewBox=VIEWBOX,
        elements=[
            svg.Defs(elements=[_bomb_gradient()]),
            *_icon_layers(transform),
        ],
    )


def _android_foreground() -> svg.SVG:
    return svg.SVG(
        width=108,
        height=108,
        viewBox=ADAPTIVE_VIEWBOX,
        elements=[
            svg.Defs(elements=[_bomb_gradient()]),
            svg.G(transform=ADAPTIVE_MARK_TRANSFORM, elements=_bomb_mark()),
        ],
    )


def _android_background() -> svg.SVG:
    return svg.SVG(
        width=108,
        height=108,
        viewBox=ADAPTIVE_VIEWBOX,
        elements=[svg.Rect(width=108, height=108, fill=ICON_BACKGROUND)],
    )


def _android_monochrome() -> svg.SVG:
    return svg.SVG(
        width=108,
        height=108,
        viewBox=ADAPTIVE_VIEWBOX,
        elements=[svg.G(transform=ADAPTIVE_MARK_TRANSFORM, elements=_monochrome_mark())],
    )


def _mask_preview() -> svg.SVG:
    """Show the safe icon under representative launcher masks."""
    masks: list[tuple[str, svg.Element, float]] = [
        ("preview-circle", svg.Circle(cx=70, cy=70, r=58), 12),
        ("preview-squircle", svg.Rect(x=152, y=12, width=116, height=116, rx=30), 152),
        ("preview-rounded", svg.Rect(x=292, y=12, width=116, height=116, rx=14), 292),
    ]
    definitions: list[svg.Element] = [_bomb_gradient()]
    tiles: list[svg.Element] = []
    for name, shape, x in masks:
        definitions.append(svg.ClipPath(id=name, elements=[shape]))
        tiles.append(
            svg.G(
                clip_path=f"url(#{name})",
                elements=[
                    svg.G(
                        transform=[svg.Translate(x, 12), svg.Scale(1.8125)],
                        elements=_icon_layers(SAFE_MARK_TRANSFORM),
                    )
                ],
            )
        )
    return svg.SVG(
        width=840,
        height=280,
        viewBox=PREVIEW_VIEWBOX,
        elements=[svg.Defs(elements=definitions), *tiles],
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
        ICON_SVG: _serialize(_app_icon(mask_safe=False)),
        MASKABLE_SVG: _serialize(_app_icon(mask_safe=True)),
        MOBILE_MASTER_SVG: _serialize(_app_icon(mask_safe=True)),
        ANDROID_FOREGROUND_SVG: _serialize(_android_foreground()),
        ANDROID_BACKGROUND_SVG: _serialize(_android_background()),
        ANDROID_MONOCHROME_SVG: _serialize(_android_monochrome()),
        MASK_PREVIEW_SVG: _serialize(_mask_preview()),
    }


def _find_tool(name: str) -> str | None:
    """Prefer tools installed beside the active Python for stable rendering."""
    environment_tool = Path(sys.executable).resolve().parent / name
    if environment_tool.is_file():
        return str(environment_tool)
    return shutil.which(name)


def _rasterizer(src: Path, out: Path, width: int, height: int) -> list[list[str]]:
    commands: list[list[str]] = []
    if converter := _find_tool("rsvg-convert"):
        commands.append([converter, "-w", str(width), "-h", str(height), "-o", str(out), str(src)])
    if converter := _find_tool("convert"):
        commands.append(
            [
                converter,
                "-background",
                "none",
                "-density",
                "384",
                "-resize",
                f"{width}x{height}!",
                str(src),
                str(out),
            ]
        )
    if converter := _find_tool("inkscape"):
        commands.append(
            [
                converter,
                str(src),
                "-w",
                str(width),
                "-h",
                str(height),
                "--export-type=png",
                f"--export-filename={out}",
            ]
        )
    return commands


def _rasterize(src: Path, out: Path, width: int, height: int) -> None:
    commands = _rasterizer(src, out, width, height)
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
    converter = _find_tool("convert")
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
    for source, path, width, height in RASTER_TARGETS:
        _rasterize(source, path, width, height)
        print(f"  generated {path.relative_to(ROOT)} ({width}x{height})")


def _check() -> None:
    stale = [path for path, expected in _svg_outputs().items() if not path.exists() or path.read_text() != expected]
    with tempfile.TemporaryDirectory(prefix="qms-artwork-") as directory:
        temporary = Path(directory)
        svg_outputs = _svg_outputs()
        for source, tracked, width, height in RASTER_TARGETS:
            temporary_source = temporary / source.name
            temporary_source.write_text(svg_outputs[source], encoding="utf-8")
            rendered = temporary / tracked.name
            _rasterize(temporary_source, rendered, width, height)
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
