"""Checks for the generated visual identity assets."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "src" / "qminesweeper" / "static" / "icons"
MOBILE = ROOT / "artwork" / "mobile"


def test_generated_artwork_is_current() -> None:
    subprocess.run(
        [sys.executable, "scripts/artwork/generate.py", "--check"],
        cwd=ROOT,
        check=True,
    )


@pytest.mark.parametrize(
    ("path", "size"),
    [
        (ICONS / "apple-touch-icon-180.png", (180, 180)),
        (ICONS / "icon-maskable-192.png", (192, 192)),
        (ICONS / "icon-maskable-512.png", (512, 512)),
        (MOBILE / "app-icon-1024.png", (1024, 1024)),
        (MOBILE / "play-store-icon-512.png", (512, 512)),
        (MOBILE / "android" / "foreground-432.png", (432, 432)),
        (MOBILE / "android" / "background-432.png", (432, 432)),
        (MOBILE / "android" / "monochrome-432.png", (432, 432)),
        (MOBILE / "mask-preview.png", (840, 280)),
    ],
)
def test_mobile_icon_dimensions(path: Path, size: tuple[int, int]) -> None:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == size


def test_manifest_declares_stable_id_and_maskable_icons() -> None:
    manifest = json.loads((ROOT / "scripts" / "pwa" / "manifest.webmanifest").read_text())
    assert manifest["id"] == "."
    maskable = {icon["src"]: icon for icon in manifest["icons"] if icon["purpose"] == "maskable"}
    assert set(maskable) == {
        "static/icons/icon-maskable-192.png",
        "static/icons/icon-maskable-512.png",
    }
    for source in maskable:
        # Manifest paths are relative to the built distribution root.
        assert (ROOT / "src" / "qminesweeper" / source).exists()
