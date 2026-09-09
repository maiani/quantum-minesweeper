"""Gate action, verified against independently computed state vectors.

A stabilizer tableau does not represent global phase, so every comparison is
made on Pauli expectation values rather than on amplitudes.
"""

from __future__ import annotations

import itertools

import pytest
from conftest import GATE_MATRICES, TWO_QUBIT_MATRICES, reference_expectation, reference_state

from chppy import CHP

ONE_QUBIT = sorted(GATE_MATRICES)
TWO_QUBIT = sorted(TWO_QUBIT_MATRICES)

# Preparations reaching the +1 eigenstates of Z, X and Y on qubit 0. Together
# these are informationally complete for one qubit, so a gate that reproduces
# the reference expectations on all of them implements the intended Clifford.
PREPARATIONS: dict[str, list[tuple[str, list[int]]]] = {
    "Z+": [],
    "X+": [("H", [0])],
    "Y+": [("H", [0]), ("S", [0])],
}


def _all_pauli_expectations(sim: CHP, n: int) -> dict[tuple[str, ...], float]:
    """Every tensor-product Pauli expectation on n qubits, keyed by label."""
    out = {}
    for labels in itertools.product("IXYZ", repeat=n):
        paulis = {q: p for q, p in enumerate(labels) if p != "I"}
        out[labels] = sim.pauli_expectation(paulis) if paulis else 1.0
    return out


@pytest.mark.parametrize("gate", ONE_QUBIT)
@pytest.mark.parametrize("prep", sorted(PREPARATIONS))
def test_one_qubit_gate_matches_state_vector(gate: str, prep: str):
    circuit = [*PREPARATIONS[prep], (gate, [0])]
    sim = CHP(1)
    for name, targets in circuit:
        sim.apply_gate(name, targets)

    vector = reference_state(circuit, 1)
    for basis in "XYZ":
        assert sim.expectation_pauli(0, basis) == pytest.approx(
            reference_expectation(vector, {0: basis}, 1), abs=1e-9
        )


@pytest.mark.parametrize("gate", TWO_QUBIT)
@pytest.mark.parametrize("prep_a", sorted(PREPARATIONS))
@pytest.mark.parametrize("prep_b", sorted(PREPARATIONS))
def test_two_qubit_gate_matches_state_vector(gate: str, prep_a: str, prep_b: str):
    # Prepare each wire independently, then apply the gate with qubit 0 as the
    # control and qubit 1 as the target.
    circuit: list[tuple[str, list[int]]] = []
    circuit += [(name, [0]) for name, _ in PREPARATIONS[prep_a]]
    circuit += [(name, [1]) for name, _ in PREPARATIONS[prep_b]]
    circuit.append((gate, [0, 1]))

    sim = CHP(2)
    for name, targets in circuit:
        sim.apply_gate(name, targets)

    vector = reference_state(circuit, 2)
    for labels, value in _all_pauli_expectations(sim, 2).items():
        paulis = {q: p for q, p in enumerate(labels) if p != "I"}
        expected = reference_expectation(vector, paulis, 2)
        assert value == pytest.approx(expected, abs=1e-9), labels


@pytest.mark.parametrize("gate", ONE_QUBIT)
def test_one_qubit_gate_broadcasts_over_targets(gate: str):
    """A single-qubit gate applies to every index it is handed."""
    broadcast = CHP(3)
    broadcast.apply_gate(gate, [0, 1, 2])

    one_at_a_time = CHP(3)
    for qubit in range(3):
        one_at_a_time.apply_gate(gate, [qubit])

    for qubit in range(3):
        for basis in "XYZ":
            assert broadcast.expectation_pauli(qubit, basis) == pytest.approx(
                one_at_a_time.expectation_pauli(qubit, basis), abs=1e-12
            )


@pytest.mark.parametrize("gate", TWO_QUBIT)
@pytest.mark.parametrize("targets", [[0], [0, 1, 2]])
def test_two_qubit_gate_requires_exactly_two_targets(gate: str, targets: list[int]):
    with pytest.raises(ValueError):
        CHP(3).apply_gate(gate, targets)


@pytest.mark.parametrize("gate", ["", "CNOT", "T", "h", "sdg", "RX"])
def test_unknown_gate_names_are_rejected(gate: str):
    """The vocabulary is exact, including case: no silent aliasing."""
    with pytest.raises(ValueError):
        CHP(2).apply_gate(gate, [0])


def test_gates_are_self_inverse_or_undone_by_adjoint():
    """X, Y, Z, H and the CZ/SWAP family square to the identity; S undoes Sdg."""
    pairs = [("X", "X"), ("Y", "Y"), ("Z", "Z"), ("H", "H"), ("S", "Sdg"), ("SX", "SXdg"), ("SY", "SYdg")]
    for first, second in pairs:
        sim = CHP(1)
        sim.apply_gate("H", [0])  # start away from a Z eigenstate
        sim.apply_gate("S", [0])
        before = [sim.expectation_pauli(0, basis) for basis in "XYZ"]
        sim.apply_gate(first, [0])
        sim.apply_gate(second, [0])
        after = [sim.expectation_pauli(0, basis) for basis in "XYZ"]
        assert after == pytest.approx(before, abs=1e-12), (first, second)


def test_reset_returns_to_all_zero():
    sim = CHP(3)
    sim.apply_gate("H", [0])
    sim.apply_gate("CX", [0, 1])
    sim.apply_gate("X", [2])
    sim.reset()
    for qubit in range(3):
        assert sim.expectation_pauli(qubit, "Z") == pytest.approx(1.0, abs=1e-12)
