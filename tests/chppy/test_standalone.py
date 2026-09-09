"""The independence contract: chppy must stay extractable.

Copies the package somewhere else and imports it with this repository absent
from sys.path, so any dependency on the vendoring application fails here rather
than at extraction time.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import chppy


def test_package_runs_outside_this_repository(tmp_path: Path):
    staged = tmp_path / "chppy"
    shutil.copytree(Path(chppy.__file__).resolve().parent, staged)

    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from chppy import CHP; "
        "sim = CHP(2); sim.apply_gate('H', [0]); sim.apply_gate('CX', [0, 1]); "
        "assert sim.entanglement_entropy([0]) == 1; "
        "assert sim.pauli_expectation({0: 'Z', 1: 'Z'}) == 1; "
        "a = sim.measure(0); assert a == sim.measure(1); "
        "print('ok')"
    )
    # -I is isolated mode: no cwd on sys.path, no user site-packages, no
    # PYTHON* environment variables. numpy still resolves from site-packages.
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
