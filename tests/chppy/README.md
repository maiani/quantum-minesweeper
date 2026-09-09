# chppy tests

Tests for the standalone `chppy` stabilizer library, phrased only in library
terms: qubits, gate-name strings, Pauli bases, and tableau invariants. Nothing
here may reference the application that vendors the library, so this directory
becomes `tests/` if the package is branched out to its own repository.

`test_standalone.py` is the independence check: it copies the package elsewhere
and imports it with this repository off `sys.path`.

Gate action is checked against state vectors that `conftest.py` builds from
explicit gate matrices, so a wrong gate would have to be wrong identically in
two independent implementations to pass. Measurement and entropy are checked
against known analytic values instead — Bell and GHZ correlations, entropies
across every cut.
