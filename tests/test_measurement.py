# tests/test_measures.py
import pytest

from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_measure_z_eigenstates(Backend: type[QuantumBackend]):
    """
    |0> measured in Z -> 0 deterministically, <Z>=+1
    X|0>=|1> measured in Z -> 1 deterministically, <Z>=-1
    """
    st = Backend().generate_stabilizer_state(1)

    # |0>
    out0 = st.measure(0, basis="Z")
    assert out0 == 0
    assert pytest.approx(st.expectation_pauli(0, "Z"), abs=1e-9) == 1.0

    # Reset and prepare |1>
    st.reset()
    st.apply_gate("X", [0])
    out1 = st.measure(0, basis="Z")
    assert out1 == 1
    assert pytest.approx(st.expectation_pauli(0, "Z"), abs=1e-9) == -1.0


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_measure_x_on_plus_collapse(Backend: type[QuantumBackend]):
    """
    H|0> = |+> is +1 eigenstate of X, so:
    - measuring in X gives outcome 0 deterministically
    - post-measurement state is an X-eigenstate with <X> ~ +1
    - repeating the X-measure returns 0 again
    """
    st = Backend().generate_stabilizer_state(1)
    st.apply_gate("H", [0])  # prepare |+>

    # First X-measure
    out = st.measure(0, basis="X")
    assert out == 0
    assert pytest.approx(st.expectation_pauli(0, "X"), abs=1e-9) == 1.0

    # Repeat measurement in X should be stable
    out2 = st.measure(0, basis="X")
    assert out2 == 0


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_measure_y_on_plus_i_collapse(Backend: type[QuantumBackend]):
    """
    S H |0> = |+i> is +1 eigenstate of Y, so:
    - measuring in Y gives outcome 0 deterministically
    - post-measurement state is a Y-eigenstate with <Y> ~ +1
    - repeating the Y-measure returns 0 again
    """
    st = Backend().generate_stabilizer_state(1)
    st.apply_gate("H", [0])  # |+>
    st.apply_gate("S", [0])  # |+i>

    # First Y-measure
    out = st.measure(0, basis="Y")
    assert out == 0

    # Post-measurement checks
    assert pytest.approx(st.expectation_pauli(0, "Y"), abs=1e-9) == 1.0
    out2 = st.measure(0, basis="Y")
    assert out2 == 0
