# src/quantum_board.py
"""
Quantum Board for Minesweeper-like Game
This module implements a quantum board for a Minesweeper-like game using Qiskit's stabilizer formalism.
It allows for qubit initialization, measurement, and application of quantum gates.
"""

import numpy as np
from qiskit import QuantumCircuit, QiskitError
from qiskit.quantum_info import Statevector, StabilizerState, Pauli, Clifford
from qiskit.circuit.library import HGate, SGate, CXGate, XGate

nbr_offsets = [(-1, -1), (-1, 0), (-1, 1),
               ( 0, -1),          ( 0, 1),
               ( 1, -1), ( 1, 0), ( 1, 1)]


win_conditions = ["CLASSIC", "ZERO"]

class QuantumBoard:
    def __init__(self, rows, cols, win_condition):
        self.rows = rows
        self.cols = cols
        self.n = rows * cols

        # Initialize board in |0⟩^⊗n
        self.qc = QuantumCircuit(self.n)
        self.state = StabilizerState(self.qc)

        self.explored = np.zeros((rows, cols), dtype=bool)
        self.status = "ONGOING"

        if win_condition in win_conditions:
            self.win_condition = win_condition
        else:
            Exception("Win conditition unsupported")
        

    def index(self, row, col):
        return row * self.cols + col

    def coords(self, idx):
        return divmod(idx, self.cols)
    
    def expectation_z(self, idx):
        label = 'I' * (self.n - idx - 1) + 'Z' + 'I' * idx
        return self.state.expectation_value(Pauli(label))

    def board_expectations(self):
        """Calculate the ⟨Z⟩ values expectations."""
        grid = np.zeros((self.rows, self.cols))
        for r in range(self.rows):
            for c in range(self.cols):
                grid[r, c] = self.expectation_z(self.index(r, c))
        return grid

    def neighbors(self, row, col):
        """4-connected neighbors only"""
        
        return [(r, c) for dr, dc in nbr_offsets
                if 0 <= (r := row + dr) < self.rows
                and 0 <= (c := col + dc) < self.cols]

    def get_clue(self, row, col):
        """Return sum of (1-⟨Z⟩)/2 on neighboring qubits."""
        idx = self.index(row, col)
        if self.expectation_z(idx) == -1:
            return 9.0
        else:
            total = 0.0
            for r, c in self.neighbors(row, col):
                idx = self.index(r, c)
                total += (1-self.expectation_z(idx))/2
            return total

    def measure(self, row, col):
        """Measure qubit and return its value."""       
        idx = self.index(row, col)
        self.explored[row, col] = True
        outcome, self.state = self.state.measure([idx])
        return outcome
        
    def measure_connected(self, row, col):
        """Recursively reveal all connected zero-clue cells."""
        to_explore = [(row, col)]

        while to_explore:
            r, c = to_explore.pop()
            self.measure(r, c)       
            clue = self.get_clue(r, c)

            if clue == 0.0:              
                for dr, dc in nbr_offsets:
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < self.rows and 0 <= nc < self.cols
                            and not self.explored[nr, nc]):
                        to_explore.append((nr, nc))

    def check_game_status(self):
        if self.win_condition == "CLASSIC":
            bombs = (1.0-self.board_expectations())/2
            if np.allclose(bombs + self.explored, 1.0):
                self.status = "WIN"
            elif np.max(bombs * self.explored) > 0.0:
                self.status = "LOSE" 
            else:
                self.status = "ONGOING"                
        elif self.win_condition == "QUANTUM":
            pass

    def probe_move(self, row, col):
        """Measure qubit and return its value."""       
        outcome = self.measure(row, col)
        self.check_game_status()    


    def apply_gate(self, gate, targets):
        """
        Apply an arbitrary single- or two-qubit Clifford gate.

        Parameters
        ----------
        gate : qiskit.circuit.Gate
            A Qiskit gate that is Clifford on 1 or 2 qubits
            (e.g. X, Y, Z, H, S/Sdg, SX/SXdg, CX, CZ, CY, SWAP, ECR, etc.).
        targets : list[int]
            Board indices of the qubits the gate acts on.
            The length of `targets` must equal the gate’s qubit count and,
            for controlled gates, follow Qiskit’s control/target order.
        """
        # 1.  Check the gate really is a Clifford and has 1 or 2 qubits
        try:
            cl = Clifford(gate)                 # raises if non-Clifford
        except QiskitError as err:
            raise ValueError(f"Gate not Clifford-compatible: {err}") from err

        if cl.num_qubits not in (1, 2):
            raise ValueError("Only 1- or 2-qubit Clifford gates are supported")

        if cl.num_qubits != len(targets):
            raise ValueError("Number of targets does not match gate arity")

        # 2.  Apply to the stabilizer state
        self.state = self.state.evolve(cl, targets)


# ___________________INIT FUNCTION_________________

def init_classical_board(dim, nbombs):
    """
    Initialize a quantum board with a given dimension and number of bombs.
    This function is for demonstration purposes and can be modified as needed.
    """

    qb = QuantumBoard(*dim, "CLASSIC")

    for n in range(nbombs):
        i = np.random.randint(0, dim[0])
        j = np.random.randint(0, dim[1])
        qb.apply_gate(XGate(), [qb.index(i, j)])

    return qb
