# tests/test_backend_parity.py
"""
Per-gate parity between the Stim and Qiskit backends.

For every gate in QuantumGate we apply it (via each backend) to a
tomographically-complete set of stabilizer input states and compare the full
set of Pauli expectation values on the involved qubits. Two Clifford
implementations that agree on all of these for an informationally-complete set
of inputs implement the same channel (up to an irrelevant global phase).

This is the test that pins the SY/SYdg decomposition (and would have caught the
historical Qiskit √Y / √Y† swap), and guards against the two backends silently
diverging on any gate.
"""

from __future__ import annotations

import itertools

import pytest
import stim
from qiskit.quantum_info import Pauli

from qminesweeper.qiskit_backend import QiskitState
from qminesweeper.quantum_backend import QuantumGate
from qminesweeper.stim_backend import StimState

TOL = 1e-9

# Single-qubit prep circuits reaching the +1 eigenstates of Z, X, Y on qubit 0.
# {|0>, |+>, |+i>} is informationally complete for one qubit.
SINGLE_PREPS: dict[str, list[tuple[str, list[int]]]] = {
    "Z+": [],
    "X+": [("H", [0])],
    "Y+": [("H", [0]), ("S", [0])],
}

TWO_QUBIT_GATES = {QuantumGate.CX, QuantumGate.CY, QuantumGate.CZ, QuantumGate.SWAP}
ONE_QUBIT_GATES = [g for g in QuantumGate if g not in TWO_QUBIT_GATES]


def _apply(state, circ: list[tuple[str, list[int]]], offset: int = 0) -> None:
    for gate, targets in circ:
        state.apply_gate(gate, [t + offset for t in targets])


def _stim_expect(state: StimState, paulis_by_q: dict[int, str], n: int) -> float:
    chars = ["I"] * n
    for q, p in paulis_by_q.items():
        chars[q] = p  # Stim PauliString: position i == qubit i
    return float(state.tab.peek_observable_expectation(stim.PauliString("".join(chars))))


def _qiskit_expect(state: QiskitState, paulis_by_q: dict[int, str], n: int) -> float:
    chars = ["I"] * n
    for q, p in paulis_by_q.items():
        chars[n - 1 - q] = p  # Qiskit label: little-endian (rightmost == qubit 0)
    return float(state.state.expectation_value(Pauli("".join(chars))).real)


def _all_paulis(n: int) -> list[dict[int, str]]:
    """All non-identity Pauli strings over n qubits, as {qubit: pauli} dicts."""
    out: list[dict[int, str]] = []
    for combo in itertools.product("IXYZ", repeat=n):
        if all(p == "I" for p in combo):
            continue
        out.append({q: p for q, p in enumerate(combo) if p != "I"})
    return out


@pytest.mark.parametrize("gate", ONE_QUBIT_GATES, ids=lambda g: g.value)
def test_one_qubit_gate_parity(gate: QuantumGate):
    paulis = _all_paulis(1)
    for prep_name, prep in SINGLE_PREPS.items():
        st = StimState(1)
        qk = QiskitState(1)
        _apply(st, prep)
        _apply(qk, prep)
        st.apply_gate(gate.value, [0])
        qk.apply_gate(gate.value, [0])
        for pauli in paulis:
            s = _stim_expect(st, pauli, 1)
            q = _qiskit_expect(qk, pauli, 1)
            assert abs(s - q) < TOL, f"{gate.value} on {prep_name}: <{pauli}> stim={s} qiskit={q}"


@pytest.mark.parametrize("gate", sorted(TWO_QUBIT_GATES, key=lambda g: g.value), ids=lambda g: g.value)
def test_two_qubit_gate_parity(gate: QuantumGate):
    paulis = _all_paulis(2)
    for (name0, prep0), (name1, prep1) in itertools.product(SINGLE_PREPS.items(), repeat=2):
        st = StimState(2)
        qk = QiskitState(2)
        _apply(st, prep0, offset=0)
        _apply(st, prep1, offset=1)
        _apply(qk, prep0, offset=0)
        _apply(qk, prep1, offset=1)
        st.apply_gate(gate.value, [0, 1])
        qk.apply_gate(gate.value, [0, 1])
        for pauli in paulis:
            s = _stim_expect(st, pauli, 2)
            q = _qiskit_expect(qk, pauli, 2)
            assert abs(s - q) < TOL, f"{gate.value} on {name0},{name1}: <{pauli}> stim={s} qiskit={q}"
