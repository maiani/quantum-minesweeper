"""Bipartite stabilizer entropy contract and backend parity."""

import itertools
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from qminesweeper.purepy_backend import PurePyBackend

try:
    from qminesweeper.stim_backend import StimBackend
except ImportError:  # pragma: no cover - optional dependency
    StimBackend = None
try:
    from qminesweeper.qiskit_backend import QiskitBackend
except ImportError:  # pragma: no cover - optional dependency
    QiskitBackend = None


BACKENDS = [backend for backend in (PurePyBackend, StimBackend, QiskitBackend) if backend is not None]


def _bell(state, a=0, b=1):
    state.apply_gate("H", [a])
    state.apply_gate("CX", [a, b])


@pytest.mark.parametrize("Backend", BACKENDS)
def test_known_regions(Backend):
    state = Backend().generate_stabilizer_state(4)
    _bell(state, 0, 1)
    _bell(state, 2, 3)
    assert state.entanglement_entropy([]) == 0
    assert state.entanglement_entropy([0]) == 1
    assert state.entanglement_entropy([1, 0]) == 0
    assert state.entanglement_entropy([0, 2]) == 2
    assert state.entanglement_entropy([0, 1, 2]) == 1
    assert state.entanglement_entropy([0, 1, 2, 3]) == 0


@pytest.mark.parametrize("Backend", BACKENDS)
def test_ghz_and_measurement(Backend):
    state = Backend().generate_stabilizer_state(3)
    state.apply_gate("H", [0])
    state.apply_gate("CX", [0, 1])
    state.apply_gate("CX", [0, 2])
    assert state.entanglement_entropy([0]) == 1
    assert state.entanglement_entropy([0, 1]) == 1
    state.measure(0)
    assert state.entanglement_entropy([0]) == 0
    assert state.entanglement_entropy([1]) == 0


@pytest.mark.parametrize("Backend", BACKENDS)
def test_local_unitary_invariance_and_query_is_non_destructive(Backend):
    state = Backend().generate_stabilizer_state(3)
    _bell(state)
    before = [state.entanglement_entropy(list(s)) for r in range(4) for s in itertools.combinations(range(3), r)]
    state.apply_gate("S", [0, 1, 2])
    after = [state.entanglement_entropy(list(s)) for r in range(4) for s in itertools.combinations(range(3), r)]
    assert after == before
    assert state.entanglement_entropy([1, 0]) == state.entanglement_entropy([0, 1])


@pytest.mark.parametrize("Backend", BACKENDS)
def test_two_qubit_gates_inside_region_preserve_boundary_entropy(Backend):
    state = Backend().generate_stabilizer_state(4)
    _bell(state, 0, 2)
    before = state.entanglement_entropy([0, 1])
    state.apply_gate("CX", [0, 1])
    state.apply_gate("SWAP", [0, 1])
    assert state.entanglement_entropy([0, 1]) == before


@pytest.mark.parametrize("Backend", BACKENDS)
def test_query_preserves_native_state_and_randomness(Backend):
    state = Backend().generate_stabilizer_state(3)
    _bell(state)
    if hasattr(state, "x"):
        native_before = (state.x.copy(), state.z.copy(), state.r.copy())
    elif hasattr(state, "tab"):
        native_before = str(state.tab.current_inverse_tableau())
    else:
        native_before = str(state.state.clifford)
    rng_before = np.random.get_state()
    for size in range(4):
        for subset in itertools.combinations(range(3), size):
            state.entanglement_entropy(list(subset))
    rng_after = np.random.get_state()
    assert rng_before[0] == rng_after[0]
    assert np.array_equal(rng_before[1], rng_after[1])
    assert rng_before[2:] == rng_after[2:]
    if hasattr(state, "x"):
        assert np.array_equal(state.x, native_before[0])
        assert np.array_equal(state.z, native_before[1])
        assert np.array_equal(state.r, native_before[2])
    elif hasattr(state, "tab"):
        assert str(state.tab.current_inverse_tableau()) == native_before
    else:
        assert str(state.state.clifford) == native_before


@pytest.mark.parametrize("Backend", BACKENDS)
@pytest.mark.parametrize("subset", [None, (0,), [True], [0.0], [0, 0], [-1], [3]])
def test_subset_validation(Backend, subset):
    state = Backend().generate_stabilizer_state(3)
    with pytest.raises((TypeError, ValueError, IndexError)):
        state.entanglement_entropy(subset)


def _statevector_entropy(circuit, subset, n=3):
    vector = np.zeros(2**n, complex)
    vector[0] = 1
    h = np.array([[1, 1], [1, -1]], complex) / np.sqrt(2)
    for gate, targets in circuit:
        if gate == "H":
            q = targets[0]
            out = vector.reshape([2] * n)
            out = np.moveaxis(out, q, 0).reshape(2, -1)
            out = h @ out
            vector = np.moveaxis(out.reshape([2] * n), 0, q).reshape(-1)
        elif gate == "S":
            q = targets[0]
            out = vector.reshape([2] * n)
            out = np.moveaxis(out, q, 0)
            out *= np.array([1, 1j]).reshape((2,) + (1,) * (n - 1))
            vector = np.moveaxis(out, 0, q).reshape(-1)
        elif gate == "CX":
            a, b = targets
            source = vector.reshape([2] * n)
            out = source.copy()
            for bits in itertools.product((0, 1), repeat=n):
                if bits[a]:
                    swapped = list(bits)
                    swapped[b] ^= 1
                    out[tuple(swapped)] = source[bits]
            vector = out.reshape(-1)
    region = list(subset)
    complement = [q for q in range(n) if q not in region]
    tensor = vector.reshape([2] * n)
    matrix = np.transpose(tensor, region + complement).reshape(2 ** len(region), -1)
    values = np.linalg.eigvalsh(matrix @ matrix.conj().T)
    values = values[values > 1e-12]
    return float(-np.sum(values * np.log2(values)))


@pytest.mark.parametrize("Backend", BACKENDS)
@pytest.mark.parametrize("n", [3, 4, 5, 6])
def test_seeded_circuits_match_statevector_oracle_for_all_regions(Backend, n):
    rng = random.Random(7000 + n)
    circuit = []
    for _ in range(2 * n + 3):
        if rng.random() < 0.65:
            circuit.append((rng.choice(["H", "S"]), [rng.randrange(n)]))
        else:
            a, b = rng.sample(range(n), 2)
            circuit.append(("CX", [a, b]))
    state = Backend().generate_stabilizer_state(n)
    for gate, targets in circuit:
        state.apply_gate(gate, targets)
    for size in range(n + 1):
        for subset in itertools.combinations(range(n), size):
            expected = _statevector_entropy(circuit, subset, n)
            assert state.entanglement_entropy(list(subset)) == pytest.approx(expected, abs=1e-9)
            complement = tuple(q for q in range(n) if q not in subset)
            assert state.entanglement_entropy(list(complement)) == pytest.approx(expected, abs=1e-9)


def test_chp_remains_standalone():
    module = Path(__file__).parents[1] / "qminesweeper" / "chp_tableau.py"
    script = (
        "import importlib.util, sys; "
        "spec=importlib.util.spec_from_file_location('standalone_chp', sys.argv[1]); "
        "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
        "s=m.CHP(2); s.apply_gate('H',[0]); s.apply_gate('CX',[0,1]); "
        "assert s.entanglement_entropy([0]) == 1"
    )
    result = subprocess.run([sys.executable, "-I", "-c", script, str(module)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
