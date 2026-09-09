"""chppy — a pure-Python stabilizer tableau simulator.

An independent implementation of the Aaronson–Gottesman CHP algorithm for
simulating stabilizer (Clifford) circuits in polynomial time. numpy is the only
dependency.

The library speaks a deliberately small vocabulary: qubit indices, gate-name
strings, and Pauli bases. It carries no notion of what a circuit is *for*, so
callers layer their own meaning on top, and nothing here imports from or refers
to whatever application vendors it. ``tableau.py`` documents the tableau
representation itself.

    >>> from chppy import CHP
    >>> sim = CHP(2)
    >>> sim.apply_gate("H", [0])
    >>> sim.apply_gate("CX", [0, 1])  # Bell pair
    >>> sim.pauli_expectation({0: "Z", 1: "Z"})
    1.0
    >>> sim.entanglement_entropy([0])  # S(A : rest), in bits
    1.0

Supported gates
---------------
Single-qubit: ``X Y Z H S Sdg SX SXdg SY SYdg``
Two-qubit:    ``CX CY CZ SWAP``

A ``dg`` suffix denotes the adjoint, so ``Sdg`` is S-dagger.

Reference: Aaronson, S. & Gottesman, D. (2004). Improved simulation of
stabilizer circuits. Phys. Rev. A 70, 052328.
https://doi.org/10.1103/PhysRevA.70.052328
"""

from __future__ import annotations

from chppy.tableau import CHP

__all__ = ["CHP"]
__version__ = "0.1.0"
