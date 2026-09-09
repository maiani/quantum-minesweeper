## Game Rules

Quantum Minesweeper is a **quantum twist** on the classic game of Minesweeper. 
Instead of fixed mines, the board is prepared in **quantum states**:  
The player interacts with the board by **measuring qubits** or **applying quantum gates**, 
and must either *identify* or *clear* the "quantum mines." In Clear mode, clearing
means driving the board to a state where no cell can produce a mine outcome.

### Options in the Advanced Setup

#### 1. Board size
Choose the number of **rows** and **columns**.  
The board contains $N = R \times C$ qubits.

#### 2. Mines & Entanglement Level

Set the number of **mines** $B$ and how they are prepared.  

- **Classical mines**: qubits initialized in the computational basis state $|1\rangle$, acting like ordinary mines in the classical game.  
- **Product stabilizers**: qubits prepared in independent stabilizer states, e.g. $|+\rangle$, $|i\rangle$.  
- **Entangled stabilizers**: groups of qubits prepared in random entangled stabilizer states (e.g. Bell pairs, GHZ-type states).  

The **expected number of mines** during play can be estimated as  
$$
\langle \text{Mines} \rangle = \sum_i p_i,
$$  
where $p_i = \tfrac{1}{2}(1 - \langle Z_i \rangle)$ is the probability that qubit $i$ contains a mine.

The **entanglement level** controls the size of stabilizer groups used to place mines:  

- **Level 0** — purely classical mines.  
- **Level 1** — mines are independent single-qubit stabilizers.  
- **Level $k$** — mines are prepared as random stabilizer states over groups of
  $k$ qubits. Level 2 can produce Bell-pair-like states, Level 3 can produce
  GHZ-type states, and so on.
  
#### 3. Win condition
- **Identify**: you win by measuring all currently safe sites without triggering a mine outcome.  
- **Clear**: you win by applying gates and measurements until every cell has mine probability zero.  
- **Sandbox**: free exploration — no win/lose condition.

#### 4. Move set
Determines which quantum operations are allowed:  

- **Classic** :
    Only measurement (`M`) and pinning (`P`).  

- **One-qubit (core set)**:
    Add $X$, $Y$, $Z$, $H$, $S$ enabling the player to defuse the mines.

- **One-qubit (complete set)**:  
    Covers the full single-qubit Clifford group by adding $S^\dagger$, $\sqrt{X}$, $\sqrt{X}^\dagger$, $\sqrt{Y}$, $\sqrt{Y}^\dagger$.  

- **Two-qubit**:
    Adds $CX$ and $SWAP$ to the core one-qubit gates.

- **Two-qubit (extended)**:
    Adds $CX$, $CY$, $CZ$, and $SWAP$ to the complete one-qubit gates. Both
    two-qubit modes enable creation and manipulation of entangled mines.

#### 5. Entanglement probes

**Entanglement probe regions** sets how much of the probe this game gets:
0 for none, 1 to weigh one area against the rest of the board, or 2 to also
compare two areas. Simple Setup chooses a count to suit the level; this
overrides it. Probing only reads the simulator, so it is not one of the moves:
it never measures a cell, applies a gate, or changes a pin.

Click cells one at a time, drag across the board to draw a rectangle, or
shift-click to extend a rectangle from the last cell you clicked. Dragging out
from a cell already in the area erases that rectangle. Cells need not be
adjacent. The selected area $A$ has entanglement entropy
$S(A)=-\mathrm{Tr}(\rho_A\log_2\rho_A)$ against the rest of the board.
The result is in bits. For independent Bell pairs, it counts the pairs crossing
the area's boundary. Selecting one member gives 1 bit, while selecting both
gives 0. A product state such as $|+\rangle$ gives 0 even though its mine
outcome is uncertain. Zero boundary entropy does not rule out entanglement
inside the selected area.

**Allow two-area probes** is off by default. Enable it to select a second,
disjoint area $B$ and see the **shared information between A and B**:
$$
I(A:B)=S(A)+S(B)-S(A\cup B).
$$
This is mutual information, which includes classical and quantum correlations.
The details show A versus the rest, B versus the rest, and both areas together
versus the rest. A Bell pair split between A and B has 2 bits of mutual
information; cells from separate independent pairs have 0. In a three-cell
GHZ state, two cells share 1 bit of mutual information, although their reduced
two-cell state is not entangled. Do not interpret general multipartite states
as a count of pair connections.

Keep the areas selected while switching to gates or measurement to compare
the diagnostic before and after a move. Revealed cells may be selected, but
cannot be targeted by gates. Readouts describe the current state conditioned
on recorded measurement outcomes. The interlocked-rings counter's sum of single-cell
entropies is separate from the selected-area entropy. Probe rules survive
reset, new games with the same settings, and browser save/restore; area
selections are temporary and clear on reset, a new game, or reload.
