"""Cross-runtime command, move-set, and gate-arity contract checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from qminesweeper.engine import command_tokens_for_moveset, parse_command
from qminesweeper.game import ALLOWED_MOVES, Action, MoveSet
from qminesweeper.quantum_backend import ONE_QUBIT_GATES, TWO_QUBIT_GATES, QuantumGate
from qminesweeper.view_context import build_config

ROOT = Path(__file__).parents[1]
RENDER_JS = ROOT / "qminesweeper" / "static" / "scripts" / "render.js"


def _frontend_tool_rows() -> dict[str, list[str]]:
    """Read render.js's JSON-compatible presentation rows."""
    source = RENDER_JS.read_text(encoding="utf-8")
    match = re.search(r"const TOOL_ROWS = (\{.*?\n\});", source, re.DOTALL)
    assert match, "render.js must declare TOOL_ROWS as a JSON-compatible object"
    return json.loads(match.group(1))


def _gate_tokens(move_set: MoveSet) -> set[str]:
    return {move.value.upper() for move in ALLOWED_MOVES[move_set] if isinstance(move, QuantumGate)}


@pytest.mark.parametrize("move_set", list(MoveSet))
def test_command_tokens_are_derived_from_allowed_moves(move_set: MoveSet):
    grouped = command_tokens_for_moveset(move_set)
    actual = set(grouped["actions"] + grouped["single"] + grouped["two"])
    expected = {
        move.value.upper() if isinstance(move, QuantumGate) else move.value
        for move in ALLOWED_MOVES[move_set]
    }

    assert actual == expected
    assert set(grouped["actions"]) <= {action.value for action in Action}
    assert set(grouped["single"]) <= {gate.value.upper() for gate in ONE_QUBIT_GATES}
    assert set(grouped["two"]) <= {gate.value.upper() for gate in TWO_QUBIT_GATES}


def test_frontend_tools_match_move_set_legality():
    rows = _frontend_tool_rows()
    exposed = {
        MoveSet.CLASSIC: set(),
        MoveSet.ONE_QUBIT: set(rows["core1"]),
        MoveSet.ONE_QUBIT_COMPLETE: set(rows["core1"] + rows["full1"]),
        MoveSet.TWO_QUBIT: set(rows["core1"] + rows["two"]),
        MoveSet.TWO_QUBIT_EXTENDED: set(rows["core1"] + rows["full1"] + rows["twoext"]),
    }

    for move_set in MoveSet:
        assert exposed[move_set] == _gate_tokens(move_set)


def test_every_frontend_gate_has_shared_arity_and_parses_with_it():
    exposed = set().union(*_frontend_tool_rows().values())
    arities = build_config()["gate_arities"]

    assert set(arities) == {gate.value.upper() for gate in QuantumGate}
    for token in exposed:
        arity = arities[token]
        command = f"{token} 1,1" if arity == 1 else f"{token} 1,1 1,2"
        parsed = parse_command(command)
        assert parsed.gate == token
        assert (parsed.cell2 is not None) is (arity == 2)
