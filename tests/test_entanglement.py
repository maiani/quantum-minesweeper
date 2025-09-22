# tests/test_entanglement.py
import pytest

from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.quantum_backend import QuantumBackend
from qminesweeper.stim_backend import StimBackend


def _prepare_bell_phi_plus(st):
    """Prepare |Φ+> = (|00> + |11>)/sqrt(2) on qubits (0,1)."""
    st.apply_gate("H", [0])
    st.apply_gate("CX", [0, 1])


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_bell_correlations_z(Backend: type[QuantumBackend]):
    """
    For |Φ+>, Z⊗Z has expectation +1 → Z outcomes are *equal* every time.
    """
    TRIALS = 20
    for _ in range(TRIALS):
        st = Backend().generate_stabilizer_state(2)
        _prepare_bell_phi_plus(st)
        a = st.measure(0, basis="Z")
        b = st.measure(1, basis="Z")
        assert a == b


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_bell_correlations_x(Backend: type[QuantumBackend]):
    """
    For |Φ+>, X⊗X has expectation +1 → X outcomes are *equal* every time.
    """
    TRIALS = 20
    for _ in range(TRIALS):
        st = Backend().generate_stabilizer_state(2)
        _prepare_bell_phi_plus(st)
        a = st.measure(0, basis="X")
        b = st.measure(1, basis="X")
        assert a == b


@pytest.mark.parametrize("Backend", [StimBackend, QiskitBackend])
def test_bell_correlations_y(Backend: type[QuantumBackend]):
    """
    For |Φ+>, Y⊗Y has expectation -1 → Y outcomes are *opposite* every time.
    """
    TRIALS = 20
    for _ in range(TRIALS):
        st = Backend().generate_stabilizer_state(2)
        _prepare_bell_phi_plus(st)
        a = st.measure(0, basis="Y")
        b = st.measure(1, basis="Y")
        assert a != b
