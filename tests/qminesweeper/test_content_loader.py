"""Tests for trusted package-owned page content."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from jinja2 import Environment, FileSystemLoader, select_autoescape

from qminesweeper.content_loader import PAGE_CONTENT, load_html_fragment, load_page_content
from scripts import build_browser

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "src" / "qminesweeper" / "content"
TEMPLATES_DIR = ROOT / "src" / "qminesweeper" / "templates"


def test_all_english_page_content_is_valid_html_fragment():
    content = load_page_content(CONTENT_DIR)

    assert set(content) == set(PAGE_CONTENT)
    for fragment in content.values():
        assert fragment.strip()
        assert "<html" not in fragment.lower()
        assert "<body" not in fragment.lower()
        ET.fromstring(f"<root>{fragment}</root>")


def test_advanced_setup_preserves_mathjax_markup():
    fragment = load_page_content(CONTENT_DIR)["advanced_setup"]

    assert '<span class="arithmatex">\\(R\\)</span>' in fragment
    assert "\\langle \\text{Mines} \\rangle" in fragment


def test_missing_fragment_has_visible_fallback(tmp_path: Path):
    assert load_html_fragment(tmp_path / "missing.html") == "<p>Not found.</p>"


def test_shared_templates_include_page_content():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    page_content = load_page_content(CONTENT_DIR)
    features = {
        "ENABLE_BROWSER_APP": False,
        "ENABLE_ENTANGLEMENT_PROBES": False,
        "ENABLE_HELP": False,
        "ENABLE_SURVEY": False,
        "PROBE_REGION_DEFAULT": 0,
        "PROBE_REGION_LIMIT": 0,
        "SURVEY_URL": "",
    }

    setup = env.get_template("_setup_content.html").render(
        page_content=page_content,
        FEATURES=features,
    )
    about = env.get_template("about.html").render(
        page_content=page_content,
        FEATURES=features,
        online_count=lambda: 0,
        version="test",
    )

    assert '<h2 id="how-to-play">How to play</h2>' in setup
    assert '<h2 id="setup-options">Setup options</h2>' in setup
    assert '<h2 id="about">About</h2>' in about


def test_browser_fingerprint_includes_every_page_fragment(monkeypatch):
    seen: list[Path] = []
    monkeypatch.setattr(build_browser, "_hash_file", lambda _hasher, path: seen.append(path))

    build_browser._build_fingerprint()

    expected = {path for path in CONTENT_DIR.rglob("*") if path.is_file()}
    assert expected <= set(seen)
