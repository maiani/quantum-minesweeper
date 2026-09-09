#!/usr/bin/env python
"""Build the static browser-only bundle into ./dist.

The bundle has no server dependency: open dist/index.html (served over http) and
the game runs entirely in the browser via Pyodide. Layout:

    dist/
      index.html              # browser entry (scripts/browser_index.html)
      static/...              # CSS + JS (incl. render.js, tools.js, pyodide-engine.js, browser-main.js)
      py/modules.json         # manifest of the Python modules to load
      py/qminesweeper/*.py    # the pure-Python engine, fetched by PyodideEngine
      py/chppy/*.py           # the vendored standalone stabilizer library

Run:   python scripts/build_browser.py
Serve: python -m http.server -d dist 8000   # then open http://127.0.0.1:8000
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Run as `python scripts/build_browser.py`, so sys.path[0] is scripts/ — a stale
# installed qminesweeper in site-packages would otherwise shadow the in-repo
# source. Put src/ first so we always build from the current tree.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from qminesweeper import __version__  # noqa: E402
from qminesweeper.docs_render import load_docs  # noqa: E402
from qminesweeper.settings import get_settings  # noqa: E402
from qminesweeper.view_context import build_config, build_features  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PKG = SRC / "qminesweeper"
CHPPY = SRC / "chppy"
DIST = ROOT / "dist"
DOCS_DIR = PKG / "docs"
PWA_DIR = ROOT / "scripts" / "pwa"  # manifest + service-worker sources (emitted at dist root)

# PWA icons the manifest references (rasterised from icon.svg by make_icons.py).
PWA_ICONS = ["icon-192.png", "icon-512.png"]

# Pure-Python modules the in-browser engine needs (numpy-only), as paths
# relative to dist/py. They are package-qualified because the bundle ships two
# importable packages: the game, and the standalone chppy library it vendors.
# Pyodide mirrors these paths under /lib, which is already on its sys.path.
PURE_MODULES = [
    "qminesweeper/__init__.py",
    "qminesweeper/quantum_backend.py",
    "qminesweeper/board.py",
    "qminesweeper/game.py",
    "qminesweeper/chppy_backend.py",
    "qminesweeper/engine.py",
    "qminesweeper/browser.py",
    "chppy/__init__.py",
    "chppy/tableau.py",
]


def _hash_file(hasher, path: Path) -> None:
    """Add a file path and contents to a deterministic build fingerprint."""
    hasher.update(str(path.relative_to(ROOT)).encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(path.read_bytes())
    hasher.update(b"\0")


def _build_fingerprint() -> str:
    """Fingerprint the files whose stale cache can break the browser build."""
    hasher = hashlib.sha256()
    for name in PURE_MODULES:
        _hash_file(hasher, SRC / name)
    for base in (PKG / "static", PWA_DIR):
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            _hash_file(hasher, path)
    for path in (
        ROOT / "scripts" / "browser_index.html",
        PKG / "templates" / "base.html",
        PKG / "templates" / "_setup_content.html",
        PKG / "templates" / "about.html",
    ):
        _hash_file(hasher, path)
    return hasher.hexdigest()[:12]


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # Use a content-derived cache id, not just the package version. Otherwise a
    # phone/PWA can keep serving an old modules.json after a browser-only backend
    # module is added without a version bump.
    cache_id = f"{__version__}-{_build_fingerprint()}"

    # 1. static assets (CSS + all JS)
    shutil.copytree(PKG / "static", DIST / "static")

    # 2. python sources fetched by PyodideEngine, plus a manifest of their names.
    py_dir = DIST / "py"
    py_dir.mkdir(parents=True)
    for name in PURE_MODULES:
        target = py_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SRC / name, target)
    # The manifest sits at the py/ root, above both packages, and is the single
    # source of truth for what the browser loads: pyodide-engine.js fetches it
    # instead of hardcoding the list, so adding a module here needs no JS edit.
    (py_dir / "modules.json").write_text(json.dumps(PURE_MODULES), encoding="utf-8")

    # 3. entry page. Render through Jinja at build time so the browser setup UI
    # uses the same template partial as the server /setup route.
    env = Environment(
        loader=FileSystemLoader([ROOT / "scripts", PKG / "templates"]),
        autoescape=select_autoescape(["html"]),
    )
    docs = load_docs(DOCS_DIR)
    template_context = {
        "BASE_URL": None,
        "STATIC_BASE": "static",
        # Browser build uses the shared shape with its fixed product defaults
        # (help on, about on, no tutorial/survey, reset always allowed).
        "FEATURES": build_features(),
        "config": build_config(),
        "docs": docs,
        "game_id": None,
        "version": __version__,
        "online_count": lambda: 0,
        "browser_setup": True,
        "browser_build": True,  # hides server-only UI (e.g. online-player count)
        "ABOUT_HREF": "about.html",
        "SETUP_HREF": "index.html",
        "build_id": cache_id,
        "GA_MEASUREMENT_ID": get_settings().GA_MEASUREMENT_ID,
    }
    index_html = env.get_template("browser_index.html").render(**template_context)
    (DIST / "index.html").write_text(index_html, encoding="utf-8")
    about_html = env.get_template("about.html").render(**template_context)
    (DIST / "about.html").write_text(about_html, encoding="utf-8")

    # 4. PWA: manifest + service worker at the dist root (the SW must sit at the
    # root so its scope covers the whole app). The SW cache name decides when
    # clients drop their cache-first cache. The package version plus content
    # fingerprint gives every changed browser bundle a fresh cache.
    shutil.copy(PWA_DIR / "manifest.webmanifest", DIST / "manifest.webmanifest")
    sw = (PWA_DIR / "sw.js").read_text(encoding="utf-8").replace("__QMS_VERSION__", cache_id)
    (DIST / "sw.js").write_text(sw, encoding="utf-8")

    # The manifest references PNG icons; they ship via the static/ copy above.
    # Fail loudly if they are missing rather than shipping a broken install.
    missing = [name for name in PWA_ICONS if not (DIST / "static" / "icons" / name).exists()]
    if missing:
        raise SystemExit(f"Missing PWA icons {missing}; run: python scripts/make_icons.py")

    files = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"Built {DIST.relative_to(ROOT)}/ ({files} files).")
    print(f"SW cache: {cache_id}")
    print("Serve:  python -m http.server -d dist 8000")
    print("Open:   http://127.0.0.1:8000")


if __name__ == "__main__":
    main()
