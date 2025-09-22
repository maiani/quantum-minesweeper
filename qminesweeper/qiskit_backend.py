# qminesweeper/qiskit_backend.py
from __future__ import annotations

from typing import Optional

from qiskit import QuantumCircuit
from qiskit.circuit.library import (
    CXGate,
    CYGate,
    CZGate,
    HGate,
    SdgGate,
    SGate,
    SwapGate,
    SXdgGate,
    SXGate,
    XGate,
    YGate,
    ZGate,
)
from qiskit.quantum_info import Clifford, Pauli, StabilizerState, random_clifford

from qminesweeper.quantum_backend import QuantumBackend, QuantumGate, StabilizerQuantumState


class QiskitState(StabilizerQuantumState):
    """
    Stabilizer state implementation using Qiskit's Clifford simulator.
    """

    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self._init_state()

    def _init_state(self) -> None:
        """Initialize stabilizer state to |0...0⟩."""
        self.state = StabilizerState(QuantumCircuit(self.n))

    # ---------- public API ----------

    def reset(self) -> None:
        """Reset the state to |0...0⟩."""
        self._init_state()

    def expectation_pauli(self, idx: int, basis: str) -> float:
        """
        Compute ⟨basis⟩ for a single qubit at index.

        Qiskit uses little-endian order for Pauli labels:
        qubit 0 corresponds to the *right-most* character.

        Parameters
        ----------
        idx : int
            Index of the qubit.
        basis : str
            Pauli basis: one of {"X", "Y", "Z"}.

        Returns
        -------
        float
            Expectation value in the given basis.
        """
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Basis must be one of 'X','Y','Z'")

        # Right-most char = qubit 0 (little-endian)
        label = "I" * (self.n - idx - 1) + basis + "I" * idx
        value = self.state.expectation_value(Pauli(label))
        return float(value.real)

    def measure(self, idx: int, basis: str = "Z") -> int:
        """
        Perform a projective measurement in the given Pauli basis.

        Parameters
        ----------
        idx : int
            Index of the qubit to measure.
        basis : str, default="Z"
            Measurement basis, one of {"X", "Y", "Z"}.

        Returns
        -------
        int
            The measurement outcome (0 or 1).
        """
        if basis == "Z":
            outcome, self.state = self.state.measure([idx])
            return int(outcome)

        if basis == "X":
            self.state = self.state.evolve(Clifford(HGate()), [idx])
            outcome, self.state = self.state.measure([idx])
            self.state = self.state.evolve(Clifford(HGate()), [idx])
            return int(outcome)

        if basis == "Y":
            # U = Sdg ∘ H, then measure Z, then undo with H ∘ S
            self.state = self.state.evolve(Clifford(SdgGate()), [idx])
            self.state = self.state.evolve(Clifford(HGate()), [idx])
            outcome, self.state = self.state.measure([idx])
            self.state = self.state.evolve(Clifford(HGate()), [idx])
            self.state = self.state.evolve(Clifford(SGate()), [idx])
            return int(outcome)

        raise ValueError("Basis must be one of 'X', 'Y', 'Z'")

    def apply_gate(self, gate: QuantumGate | str, targets: list[int]) -> None:
        """
        Apply a supported Clifford gate.

        Parameters
        ----------
        gate : QuantumGate | str
            The gate to apply. Can be passed as a QuantumGate enum or as a string
            (e.g. "X", "H").
        targets : list[int]
            Indices of the target qubits.

        Raises
        ------
        ValueError
            If the gate is unsupported or applied to the wrong number of qubits.
        """
        if isinstance(gate, str):
            try:
                gate_enum = QuantumGate[gate]
            except KeyError:
                raise ValueError(f"Unsupported gate string: {gate}")
        else:
            gate_enum = gate

        # --- one-qubit gates ---
        if gate_enum == QuantumGate.X:
            cl = Clifford(XGate())
        elif gate_enum == QuantumGate.Y:
            cl = Clifford(YGate())
        elif gate_enum == QuantumGate.Z:
            cl = Clifford(ZGate())
        elif gate_enum == QuantumGate.H:
            cl = Clifford(HGate())
        elif gate_enum == QuantumGate.S:
            cl = Clifford(SGate())
        elif gate_enum == QuantumGate.Sdg:
            cl = Clifford(SdgGate())
        elif gate_enum == QuantumGate.SXdg:
            cl = Clifford(SXdgGate())
        elif gate_enum == QuantumGate.SY:
            for t in targets:
                self.state = self.state.evolve(Clifford(SGate()), [t])
                self.state = self.state.evolve(Clifford(SXGate()), [t])
                self.state = self.state.evolve(Clifford(SdgGate()), [t])
            return
        elif gate_enum == QuantumGate.SYdg:
            for t in targets:
                self.state = self.state.evolve(Clifford(SGate()), [t])
                self.state = self.state.evolve(Clifford(SXdgGate()), [t])
                self.state = self.state.evolve(Clifford(SdgGate()), [t])
            return

        # --- two-qubit gates ---
        elif gate_enum == QuantumGate.CX:
            cl = Clifford(CXGate())
        elif gate_enum == QuantumGate.CY:
            cl = Clifford(CYGate())
        elif gate_enum == QuantumGate.CZ:
            cl = Clifford(CZGate())
        elif gate_enum == QuantumGate.SWAP:
            cl = Clifford(SwapGate())
        else:
            raise ValueError(f"Unsupported gate: {gate_enum}")

        if cl.num_qubits != len(targets):
            raise ValueError(f"Gate {gate_enum} expects {cl.num_qubits} qubits, got {len(targets)}")
        self.state = self.state.evolve(cl, targets)


class QiskitBackend(QuantumBackend):
    """
    Qiskit-based stabilizer backend for Quantum Minesweeper.
    """

    def generate_stabilizer_state(self, n_qubits: int) -> StabilizerQuantumState:
        """Initialize a fresh stabilizer state with `n_qubits`."""
        return QiskitState(n_qubits)

    def random_clifford_circuit(self, k: int, *, seed: Optional[int] = None) -> list[tuple[str, list[int]]]:
        """
        Generate a random Clifford on `k` qubits and return as a circuit.

        Parameters
        ----------
        k : int
            Number of qubits.
        seed : Optional[int]
            RNG seed for reproducibility.

        Returns
        -------
        list[tuple[str, list[int]]]
            A list of (gate_name, target_qubits).
        """
        if k <= 0:
            return []
        cl = random_clifford(k, seed=seed)
        qc = cl.to_circuit()

        out: list[tuple[str, list[int]]] = []
        for instr in qc.data:
            name = instr.operation.name.upper()
            if name == "SDG":
                name = "Sdg"  # canonicalize
            tloc = [qc.qubits.index(q) for q in instr.qubits]
            out.append((name, tloc))
        return out
