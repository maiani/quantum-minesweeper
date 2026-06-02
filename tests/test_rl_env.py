from __future__ import annotations

import pytest

pytest.importorskip("gymnasium")

from qminesweeper.rl_env import QuantumMinesweeperEnv


def test_classic_rl_env_uses_measure_actions_without_pins():
    env = QuantumMinesweeperEnv(rows=2, cols=2, mines=0, backend="purepy")

    assert env.action_space.n == 4
    assert env.action_meanings == ["M 1,1", "M 1,2", "M 2,1", "M 2,2"]

    obs, info = env.reset(seed=0)
    assert obs.shape == (4,)
    assert info["actions"] == env.action_meanings

    obs, reward, terminated, truncated, info = env.step(0)
    assert obs.shape == (4,)
    assert reward >= 0
    assert not truncated
    assert "command" in info
    assert isinstance(terminated, bool)


def test_two_qubit_ruleset_expands_action_space_without_pins():
    env = QuantumMinesweeperEnv(rows=2, cols=2, mines=0, move_set="two", win_condition="sandbox", backend="purepy")

    # TWO_QUBIT allows M, five 1Q gates (X,Y,Z,H,S), and three 2Q gates
    # (CX,CZ,SWAP). Pins are deliberately omitted.
    assert env.action_space.n == 4 + 5 * 4 + 3 * 4 * 3
    assert not any(action.startswith("P ") for action in env.action_meanings)
    assert "CX 1,1 1,2" in env.action_meanings
