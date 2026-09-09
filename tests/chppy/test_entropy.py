"""Bipartite entanglement entropy S(subset : complement), in bits."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from chppy import CHP


def test_product_state_has_zero_entropy():
    sim = CHP(3)
    sim.apply_gate("H", [0])
    sim.apply_gate("S", [1])
    for size in range(4):
        for subset in itertools.combinations(range(3), size):
            assert sim.entanglement_entropy(list(subset)) == pytest.approx(0.0, abs=1e-12)


def test_bell_pair_has_one_bit(bell: CHP):
    assert bell.entanglement_entropy([0]) == pytest.approx(1.0, abs=1e-12)
    assert bell.entanglement_entropy([1]) == pytest.approx(1.0, abs=1e-12)


def test_empty_and_full_subsets_have_zero_entropy(bell: CHP):
    """A cut with nothing on one side is not a cut."""
    assert bell.entanglement_entropy([]) == pytest.approx(0.0, abs=1e-12)
    assert bell.entanglement_entropy([0, 1]) == pytest.approx(0.0, abs=1e-12)


def test_entropy_equals_that_of_the_complement():
    """S(A : rest) = S(rest : A) for a pure state."""
    sim = CHP(4)
    sim.apply_gate("H", [0])
    sim.apply_gate("CX", [0, 1])
    sim.apply_gate("H", [2])
    sim.apply_gate("CX", [2, 3])
    sim.apply_gate("CZ", [1, 2])
    for size in range(5):
        for subset in itertools.combinations(range(4), size):
            complement = [q for q in range(4) if q not in subset]
            assert sim.entanglement_entropy(list(subset)) == pytest.approx(
                sim.entanglement_entropy(complement), abs=1e-12
            )


def test_ghz_has_one_bit_across_every_nontrivial_cut():
    sim = CHP(4)
    sim.apply_gate("H", [0])
    for target in (1, 2, 3):
        sim.apply_gate("CX", [0, target])
    for size in range(1, 4):
        for subset in itertools.combinations(range(4), size):
            assert sim.entanglement_entropy(list(subset)) == pytest.approx(1.0, abs=1e-12)


def test_stacked_bell_pairs_count_cut_pairs():
    """Two independent pairs: entropy counts the pairs the cut separates."""
    sim = CHP(4)
    sim.apply_gate("H", [0])
    sim.apply_gate("CX", [0, 1])
    sim.apply_gate("H", [2])
    sim.apply_gate("CX", [2, 3])
    assert sim.entanglement_entropy([0]) == pytest.approx(1.0, abs=1e-12)
    assert sim.entanglement_entropy([0, 2]) == pytest.approx(2.0, abs=1e-12)
    assert sim.entanglement_entropy([0, 1]) == pytest.approx(0.0, abs=1e-12)


def test_local_gates_do_not_change_the_cut(bell: CHP):
    """Single-qubit gates inside a region leave its boundary entropy alone."""
    before = bell.entanglement_entropy([0])
    for gate in ("H", "S", "X", "SY"):
        bell.apply_gate(gate, [0])
    assert bell.entanglement_entropy([0]) == pytest.approx(before, abs=1e-12)


def test_query_is_non_destructive_and_consumes_no_randomness(bell: CHP):
    """Reading entropy must not disturb the state or the random stream."""
    tableau_before = (bell.x.copy(), bell.z.copy(), bell.r.copy())
    np.random.seed(7)
    rng_before = np.random.get_state()
    for size in range(3):
        for subset in itertools.combinations(range(2), size):
            bell.entanglement_entropy(list(subset))
    rng_after = np.random.get_state()

    assert np.array_equal(bell.x, tableau_before[0])
    assert np.array_equal(bell.z, tableau_before[1])
    assert np.array_equal(bell.r, tableau_before[2])
    assert rng_before[1].tolist() == rng_after[1].tolist()


@pytest.mark.parametrize("subset", [None, (0,), [True], [0.0], "01", 0])
def test_malformed_subsets_raise_type_error(subset):
    with pytest.raises(TypeError):
        CHP(3).entanglement_entropy(subset)


def test_duplicate_indices_raise_value_error():
    with pytest.raises(ValueError):
        CHP(3).entanglement_entropy([0, 0])


@pytest.mark.parametrize("subset", [[-1], [3], [0, 3]])
def test_out_of_range_indices_raise_index_error(subset):
    with pytest.raises(IndexError):
        CHP(3).entanglement_entropy(subset)
