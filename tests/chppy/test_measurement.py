"""Projective measurement: outcomes, collapse, and correlations."""

from __future__ import annotations

import numpy as np
import pytest

from chppy import CHP


def test_measuring_a_fresh_state_gives_zero():
    sim = CHP(3)
    assert [sim.measure(q) for q in range(3)] == [0, 0, 0]


def test_measurement_is_idempotent():
    """Re-measuring a collapsed qubit repeats the same outcome."""
    sim = CHP(2)
    sim.apply_gate("H", [0])
    first = sim.measure(0)
    assert all(sim.measure(0) == first for _ in range(10))


def test_bell_pair_outcomes_are_equal(bell: CHP):
    """(|00> + |11>)/sqrt(2): the two outcomes always agree."""
    assert bell.measure(0) == bell.measure(1)


def test_bell_pair_is_unbiased_over_many_shots():
    """Each Bell outcome appears roughly half the time.

    A loose bound, chosen so the test is about the outcome distribution rather
    than about any particular random stream.
    """
    np.random.seed(20240101)
    ones = 0
    shots = 400
    for _ in range(shots):
        sim = CHP(2)
        sim.apply_gate("H", [0])
        sim.apply_gate("CX", [0, 1])
        ones += sim.measure(0)
    assert 0.35 * shots < ones < 0.65 * shots


def test_ghz_outcomes_are_all_equal():
    sim = CHP(4)
    sim.apply_gate("H", [0])
    for target in (1, 2, 3):
        sim.apply_gate("CX", [0, target])
    outcomes = [sim.measure(q) for q in range(4)]
    assert len(set(outcomes)) == 1


def test_measurement_collapses_the_partner():
    """After measuring one half of a Bell pair, the other is deterministic."""
    sim = CHP(2)
    sim.apply_gate("H", [0])
    sim.apply_gate("CX", [0, 1])
    outcome = sim.measure(0)
    expected_z = 1.0 if outcome == 0 else -1.0
    assert sim.expectation_pauli(1, "Z") == pytest.approx(expected_z, abs=1e-12)


@pytest.mark.parametrize("basis", ["X", "Y", "Z"])
def test_measurement_pins_the_measured_basis(basis: str):
    """Whatever basis is measured, that observable becomes deterministic."""
    sim = CHP(1)
    sim.apply_gate("H", [0])
    sim.apply_gate("S", [0])
    outcome = sim.measure(0, basis)
    assert outcome in (0, 1)
    expected = 1.0 if outcome == 0 else -1.0
    assert sim.expectation_pauli(0, basis) == pytest.approx(expected, abs=1e-12)


def test_x_basis_measurement_of_plus_is_deterministic():
    sim = CHP(1)
    sim.apply_gate("H", [0])  # |+>, a +1 eigenstate of X
    assert sim.measure(0, "X") == 0


@pytest.mark.parametrize("basis", ["", "A", "x", "ZZ"])
def test_invalid_measurement_basis_is_rejected(basis: str):
    with pytest.raises(ValueError):
        CHP(1).measure(0, basis)


@pytest.mark.parametrize("basis", ["", "A", "z", "XY"])
def test_invalid_expectation_basis_is_rejected(basis: str):
    with pytest.raises(ValueError):
        CHP(1).expectation_pauli(0, basis)
