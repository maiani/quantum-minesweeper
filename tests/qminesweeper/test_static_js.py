"""Lightweight checks for framework-free static JavaScript."""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC_SCRIPTS = ROOT / "src" / "qminesweeper" / "static" / "scripts"
BASE_TEMPLATE = ROOT / "src" / "qminesweeper" / "templates" / "base.html"
HELP_CSS = ROOT / "src" / "qminesweeper" / "static" / "styles" / "help.css"
HELP_JS = STATIC_SCRIPTS / "help.js"
LAYOUT_JS = STATIC_SCRIPTS / "layout.js"
PIN_HELP = ROOT / "src" / "qminesweeper" / "static" / "help" / "P-move"


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


@pytest.mark.parametrize(
    ("saved", "expected_active"),
    [("__missing__", False), ("0", False), ("1", True)],
)
def test_help_defaults_closed_but_respects_saved_choice(saved: str, expected_active: bool):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; static JavaScript behavior check skipped")

    harness = r"""
const source = require("fs").readFileSync(process.argv[1], "utf8");
const saved = process.argv[2];
const values = saved === "__missing__" ? {} : {qms_help_open: saved};
const element = () => ({
  attrs: {},
  classList: {
    values: new Set(),
    toggle(name, force) {
      if (force) this.values.add(name); else this.values.delete(name);
    },
    contains(name) { return this.values.has(name); },
  },
  setAttribute(name, value) { this.attrs[name] = value; },
  addEventListener() {},
});
const panel = element();
const toggle = element();
global.window = {QMS_ENABLE_HELP: true};
global.localStorage = {
  getItem(key) { return Object.hasOwn(values, key) ? values[key] : null; },
  setItem(key, value) { values[key] = value; },
};
global.document = {
  getElementById(id) { return id === "sidebar" ? panel : id === "toggle-help" ? toggle : null; },
  addEventListener() {},
};
eval(source);
process.stdout.write(JSON.stringify({
  active: panel.classList.contains("active"),
  hidden: panel.attrs["aria-hidden"],
  toggleActive: toggle.classList.contains("active"),
}));
"""
    result = subprocess.run(
        [node, "-e", harness, str(HELP_JS), saved],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    expected = str(expected_active).lower()
    assert result.stdout == (
        f'{{"active":{expected},"hidden":"{str(not expected_active).lower()}",'
        f'"toggleActive":{expected}}}'
    )


def test_pin_help_visual_references_valid_logo_flag_svg():
    visual = (PIN_HELP / "visual.html").read_text(encoding="utf-8")
    name = "logo-flag.svg"

    assert name in visual
    ET.parse(PIN_HELP / "svgs" / name)


def test_layout_publishes_real_header_height_for_fixed_panels():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; static JavaScript behavior check skipped")

    harness = r"""
const source = require("fs").readFileSync(process.argv[1], "utf8");
const values = {};
const header = {offsetHeight: 73};
global.document = {
  documentElement: {style: {setProperty(name, value) { values[name] = value; }}},
  querySelector(selector) { return selector === ".app-header" ? header : null; },
};
global.window = {addEventListener() {}};
global.ResizeObserver = class {
  constructor(callback) { this.callback = callback; }
  observe(target) {
    if (target !== header) throw new Error("observed the wrong element");
    this.callback();
  }
};
eval(source);
process.stdout.write(JSON.stringify(values));
"""
    result = subprocess.run(
        [node, "-e", harness, str(LAYOUT_JS)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout == '{"--app-header-block-size":"73px"}'


def test_desktop_help_header_uses_measured_offset_without_scrollable_spacer():
    template = BASE_TEMPLATE.read_text(encoding="utf-8")
    css = HELP_CSS.read_text(encoding="utf-8")

    assert 'id="sidebar-spacer"' not in template
    assert "top: var(--app-header-block-size, 0px);" in css
    assert "#sidebar-header {\n  position: sticky;\n  top: 0;" in css
