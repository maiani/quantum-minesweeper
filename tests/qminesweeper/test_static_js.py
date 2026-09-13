"""Lightweight checks for framework-free static JavaScript."""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC_SCRIPTS = ROOT / "src" / "qminesweeper" / "static" / "scripts"
HELP_JS = STATIC_SCRIPTS / "help.js"
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
