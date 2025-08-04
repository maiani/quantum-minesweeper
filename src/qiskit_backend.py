from backend import QuantumBackend
from qiskit import QuantumCircuit
from qiskit.quantum_info import StabilizerState, Pauli, Clifford
from qiskit.circuit.library import XGate, YGate, ZGate, HGate, SGate, CXGate


class QiskitBackend(QuantumBackend):
    def __init__(self, n_qubits: int):
        super().__init__(n_qubits)
        self.state = StabilizerState(QuantumCircuit(n_qubits))

    def expectation_z(self, idx: int) -> float:
        label = 'I' * (self.n - idx - 1) + 'Z' + 'I' * idx
        return self.state.expectation_value(Pauli(label))

    def measure(self, idx: int) -> int:
        outcome, self.state = self.state.measure([idx])
        return outcome

    def apply_gate(self, gate: str, targets: list[int]):
        gate_map = {
            "X": XGate,
            "Y": YGate,
            "Z": ZGate,
            "H": HGate,
            "S": SGate,
            "CX": CXGate,
        }

        gate_cls = gate_map.get(gate)

        if gate_cls is None:
            raise ValueError(f"Unsupported gate: {gate}")

        gate_obj = gate_cls()
        cl = Clifford(gate_obj)

        if cl.num_qubits != len(targets):
            raise ValueError(f"Gate {gate} expects {cl.num_qubits} qubits, got {len(targets)}")

        self.state = self.state.evolve(cl, targets)
