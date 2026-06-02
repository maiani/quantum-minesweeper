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
- **Level $k$** — mines are prepared as random stabilizer states over groups of $k$ qubits. At Level 2 may produce Bell pairs, Level 3 GHZ-type states, etc.
  
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
    Full Clifford set: $CX$, $CY$, $CZ$, $SWAP$.  
    Enables creation and manipulation of entangled mines.
