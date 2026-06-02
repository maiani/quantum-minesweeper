# tests/test_backend_parity.py
"""
Per-gate parity across all backends (Stim, Qiskit, PurePy).

For every gate in QuantumGate we apply it (via each backend) to a
tomographically-complete set of stabilizer input states and compare the full
set of Pauli expectation values on the involved qubits. Two Clifford
implementations that agree on all of these for an informationally-complete set
of inputs implement the same channel (up to global phase).

Stim is the reference. This pins the SY/SYdg decompositions for Qiskit and
PurePy and guards against any backend silently diverging.
"""

from __future__ import annotations

import itertools

import pytest
import stim
from qiskit.quantum_info import Pauli

from qminesweeper.purepy_backend import PurePyState
from qminesweeper.qiskit_backend import QiskitState
from qminesweeper.quantum_backend import ONE_QUBIT_GATES, TWO_QUBIT_GATES, QuantumGate
from qminesweeper.stim_backend import StimState

TOL = 1e-9

# Single-qubit prep circuits reaching the +1 eigenstates of Z, X, Y on qubit 0.
# {|0>, |+>, |+i>} is informationally complete for one qubit.
SINGLE_PREPS: dict[str, list[tuple[str, list[int]]]] = {
    "Z+": [],
    "X+": [("H", [0])],
    "Y+": [("H", [0]), ("S", [0])],
}

ONE_Q = sorted(ONE_QUBIT_GATES, key=lambda g: g.value)
TWO_Q = sorted(TWO_QUBIT_GATES, key=lambda g: g.value)


def _apply(state, circ: list[tuple[str, list[int]]], offset: int = 0) -> None:
    for gate, targets in circ:
        state.apply_gate(gate, [t + offset for t in targets])


def _stim_expect(state: StimState, paulis: dict[int, str], n: int) -> float:
    chars = ["I"] * n
    for q, p in paulis.items():
        chars[q] = p  # Stim PauliString: position i == qubit i
    return float(state.tab.peek_observable_expectation(stim.PauliString("".join(chars))))


def _qiskit_expect(state: QiskitState, paulis: dict[int, str], n: int) -> float:
    chars = ["I"] * n
    for q, p in paulis.items():
        chars[n - 1 - q] = p  # Qiskit label: little-endian (rightmost == qubit 0)
    return float(state.state.expectation_value(Pauli("".join(chars))).real)


def _purepy_expect(state: PurePyState, paulis: dict[int, str], n: int) -> float:
    return state.pauli_expectation(paulis)


# name -> (state factory, expectation fn)
BACKENDS = {
    "stim": (StimState, _stim_expect),
    "qiskit": (QiskitState, _qiskit_expect),
    "purepy": (PurePyState, _purepy_expect),
}
OTHERS = [name for name in BACKENDS if name != "stim"]


def _all_paulis(n: int) -> list[dict[int, str]]:
    out: list[dict[int, str]] = []
    for combo in itertools.product("IXYZ", repeat=n):
        if all(p == "I" for p in combo):
            continue
        out.append({q: p for q, p in enumerate(combo) if p != "I"})
    return out


@pytest.mark.parametrize("gate", ONE_Q, ids=lambda g: g.value)
def test_one_qubit_gate_parity(gate: QuantumGate):
    paulis = _all_paulis(1)
    for prep_name, prep in SINGLE_PREPS.items():
        states = {name: factory(1) for name, (factory, _) in BACKENDS.items()}
        for st in states.values():
            _apply(st, prep)
            st.apply_gate(gate.value, [0])
        ref = {tuple(sorted(p.items())): BACKENDS["stim"][1](states["stim"], p, 1) for p in paulis}
        for name in OTHERS:
            expect = BACKENDS[name][1]
            for p in paulis:
                got = expect(states[name], p, 1)
                want = ref[tuple(sorted(p.items()))]
                assert abs(got - want) < TOL, f"{name} {gate.value} on {prep_name}: <{p}> {got} != stim {want}"


@pytest.mark.parametrize("gate", TWO_Q, ids=lambda g: g.value)
def test_two_qubit_gate_parity(gate: QuantumGate):
    paulis = _all_paulis(2)
    for (name0, prep0), (name1, prep1) in itertools.product(SINGLE_PREPS.items(), repeat=2):
        states = {name: factory(2) for name, (factory, _) in BACKENDS.items()}
        for st in states.values():
            _apply(st, prep0, offset=0)
            _apply(st, prep1, offset=1)
            st.apply_gate(gate.value, [0, 1])
        ref = {tuple(sorted(p.items())): BACKENDS["stim"][1](states["stim"], p, 2) for p in paulis}
        for name in OTHERS:
            expect = BACKENDS[name][1]
            for p in paulis:
                got = expect(states[name], p, 2)
                want = ref[tuple(sorted(p.items()))]
                assert abs(got - want) < TOL, f"{name} {gate.value} on {name0},{name1}: <{p}> {got} != stim {want}"
