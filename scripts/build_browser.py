#!/usr/bin/env python
"""Build the static browser-only bundle into ./dist.

The bundle has no server dependency: open dist/index.html (served over http) and
the game runs entirely in the browser via Pyodide. Layout:

    dist/
      index.html              # browser entry (scripts/browser_index.html)
      static/...              # CSS + JS (incl. render.js, tools.js, pyodide-engine.js, browser-main.js)
      py/qminesweeper/*.py    # the pure-Python engine, fetched by PyodideEngine

Run:   python scripts/build_browser.py
Serve: python -m http.server -d dist 8000   # then open http://127.0.0.1:8000
"""

from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from qminesweeper import __version__
from qminesweeper.docs_render import load_docs

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "qminesweeper"
DIST = ROOT / "dist"
DOCS_DIR = PKG / "docs"

# Pure-Python modules the in-browser engine needs (Stim-free, numpy-only).
PURE_MODULES = [
    "__init__.py",
    "quantum_backend.py",
    "board.py",
    "game.py",
    "purepy_backend.py",
    "engine.py",
    "browser.py",
]


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # 1. static assets (CSS + all JS)
    shutil.copytree(PKG / "static", DIST / "static")

    # 2. python sources fetched by PyodideEngine
    py_dir = DIST / "py" / "qminesweeper"
    py_dir.mkdir(parents=True)
    for name in PURE_MODULES:
        shutil.copy(PKG / name, py_dir / name)

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
        "FEATURES": {
            "ENABLE_HELP": True,
            "ENABLE_TUTORIAL": False,
            "TUTORIAL_URL": None,
            "ENABLE_SURVEY": False,
            "SURVEY_URL": None,
            "ENABLE_ABOUT": True,
            "RESET_POLICY": "any",
        },
        "config": {"reset_policy": "any", "enable_survey": False, "survey_url": None},
        "docs": docs,
        "game_id": None,
        "version": __version__,
        "online_count": lambda: 0,
        "browser_setup": True,
        "ABOUT_HREF": "about.html",
        "SETUP_HREF": "index.html",
    }
    index_html = env.get_template("browser_index.html").render(**template_context)
    (DIST / "index.html").write_text(index_html, encoding="utf-8")
    about_html = env.get_template("about.html").render(**template_context)
    (DIST / "about.html").write_text(about_html, encoding="utf-8")

    files = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"Built {DIST.relative_to(ROOT)}/ ({files} files).")
    print("Serve:  python -m http.server -d dist 8000")
    print("Open:   http://127.0.0.1:8000")


if __name__ == "__main__":
    main()
