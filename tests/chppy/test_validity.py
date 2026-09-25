"""``CHP.is_valid``: the structural check for arrays written from outside."""

from __future__ import annotations

import numpy as np
import pytest

from chppy import CHP


def _scrambled(n: int, seed: int) -> CHP:
    """A state reached by a seeded random circuit with measurements mixed in."""
    rng = np.random.default_rng(seed)
    sim = CHP(n)
    for _ in range(12 * n):
        roll = rng.random()
        if roll < 0.4:
            sim.apply_gate(str(rng.choice(["H", "S", "SX", "Y"])), [int(rng.integers(n))])
        elif roll < 0.85:
            a, b = (int(q) for q in rng.choice(n, size=2, replace=False))
            sim.apply_gate(str(rng.choice(["CX", "CY", "CZ", "SWAP"])), [a, b])
        else:
            sim.measure(int(rng.integers(n)), str(rng.choice(["X", "Y", "Z"])))
    return sim


@pytest.mark.parametrize("n", [1, 2, 5, 9])
def test_fresh_state_is_valid(n: int):
    assert CHP(n).is_valid()


@pytest.mark.parametrize("seed", range(5))
def test_gates_and_measurements_keep_the_tableau_valid(seed: int):
    np.random.seed(seed)  # measurement outcomes draw from the global stream
    assert _scrambled(6, seed).is_valid()


def test_a_qubit_zeroed_out_of_every_row_is_invalid():
    """The damage a two-qubit gate on one qubit used to do."""
    sim = _scrambled(4, 0)
    sim.x[:, 2] = 0
    sim.z[:, 2] = 0
    assert not sim.is_valid()


def test_a_repeated_stabilizer_is_invalid():
    sim = _scrambled(4, 1)
    sim.x[5] = sim.x[4]
    sim.z[5] = sim.z[4]
    assert not sim.is_valid()


def test_non_binary_entries_are_invalid():
    sim = CHP(3)
    sim.z[3, 0] = 2
    assert not sim.is_valid()


def test_wrong_shape_is_invalid():
    sim = CHP(3)
    sim.x = np.zeros((6, 3), dtype=np.uint8)
    assert not sim.is_valid()


def test_phase_bits_are_unconstrained():
    sim = _scrambled(3, 2)
    sim.r[:6] ^= 1
    assert sim.is_valid()
