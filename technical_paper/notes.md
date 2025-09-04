Quantum Minesweeper
===================

Introduction
------------

Minesweeper is a classical, widely known game in which the user is
presented with a hidden grid of cells. Some of these cells contain
mines, while others are safe. By clicking on a cell, the player either
reveals a number indicating how many adjacent cells contain mines, or
triggers a mine and loses the game. The challenge lies in deducing the
locations of all mines using logical reasoning and the numerical clues,
while avoiding any accidental detonations.

In this paper, we explore a quantum extension of Minesweeper. Quantum
Minesweeper has strong pedagogical potential as an accessible
introduction to fundamental concepts in quantum physics. It can
naturally illustrate notions such as superposition, measurement, the
Bloch sphere, and quantum gates, as well as more advanced topics like
entanglement, stabilizer states, and other quantum states.

Beyond its educational value, the game raises interesting open questions
about solvability. Depending on the chosen set of rules and the density
of mines, Quantum Minesweeper can be exactly solvable, computationally
hard, or even unsolvable under reasonable constraints.

In this work, we: - Propose a framework for Quantum Minesweeper,
including several possible rule variations. - Present an implementation
with both textual and graphical user interfaces. - Discuss the
solvability of the game in an abstract setting. - Use a reinforcement
learning (RL) agent to explore practical solvability. - Examine
potential pedagogical applications of the game.

Quantum Minesweeper (Rule)
--------------------------

### Recap of classical minesweeper

Players are given a two-dimensional lattice with $N = R \times L$ sites,
of which $M$ are randomly assigned to contain mines. The configuration
of mines is hidden from the player at the start. When a site without a
mine is uncovered, it displays a numerical value equal to the number of
mines in its immediate neighborhood---typically the eight adjacent cells
in the neighborhood on a square grid. This numerical clue allows the
player to infer information about the surrounding hidden cells.

The objective is to uncover all non-mine sites while avoiding any mine
detonations. If a mine-containing site is selected, the game ends
immediately in failure. The challenge lies in using the numerical clues
to perform logical deductions, ruling out mine positions and
progressively expanding the set of safe cells. In the early stages of
the game, uncovering a cell often reveals a large connected cluster of
safe sites (sometimes called a flood fill), providing a strong initial
foothold. As the game progresses, however, the available safe moves
become less obvious, and the player must rely on increasingly intricate
patterns of logical inference. \#\#\# Making Minesweeper quantum


### Quantization of Minesweeper
To formulate a quantum version of the game, we can follow these general
steps:

1.  **Promote the board to a Hilbert space** --- Represent the
    underlying classical configuration in terms of quantum states.\
2.  **Select the allowed moves** --- Define the set of quantum
    operations (unitary gates, measurements, or both) that the player
    may apply.\
3.  **Choose a clue mechanism** --- Specify how the game provides
    information about the state (e.g., through projective measurements,
    POVMs, or other observable outcomes).\
4.  **Define winning and losing conditions** --- Establish the criteria
    for a successful game completion or failure in the quantum setting.

Let us begin with the most general Hilbert space.
Consider a board with $N = R \times L$ cells.
The full game state is described by a tuple\
$$S = (S_m, S_e)$$ where:\
- $S_m \in \mathcal{H}$, with $\mathcal{H}$ being the Hilbert space of $N$ qubits representing the mine
configuration;
- $S_e$ is a classical bitstring of length $N$ marking the explored
(revealed) cells.

We define the **mine basis state** at site $i$ as $| 1 \rangle_i$ 
, indicating that the cell contains a mine, and $| 0 \rangle_i$
indicating that it does not. Equivalently, the **mine operator** at site
$i$ can be written as
$$ M_i = \frac{\mathbb{I}_2 - Z_i}{2}, $$ 
where $Z_i$ is the Pauli $Z$ operator acting on qubit $i$. This operator satisfies
$$ \langle M_i \rangle = 1
\quad \text{if the cell contains a mine,} $$ and\
$$ \langle M_i \rangle = 0
\quad \text{otherwise}. $$

In the most general setting, the quantum board state $S_m$ can be in
a superposition of different mine configurations, allowing the
possibility of quantum interference between classical layouts. This
introduces a rich new structure to the game: clues and player actions
can collapse or partially collapse the state, entangle cells, and even
create non-classical correlations between distant parts of the board.

#### Quantum clue mechanism

We define the **clue operator** for cell $i$ as
$$
C_i = \sum_{j \in \mathcal{N}(i)} M_j
= \frac{1}{2} \sum_{j \in \mathcal{N}(i)} \left( \mathbb{I}_2 - Z_j \right),
$$
where $\mathcal{N}(i)$ is the set of neighboring cells of $i$, and $M_j$ is the mine operator at site $j$. The eigenvalues of $C_i$ are the integers $0,1,\dots,|\mathcal{N}(i)|$, corresponding to the number of neighboring mines.

A *clue query* at site $i$ can be implemented in several ways:

1. **Projective readout (exact count).**  
   Perform a projective measurement of $C_i$ in its eigenbasis.  
   - **Outcome:** An integer $c_i \in \{0,\dots,|\mathcal{N}(i)|\}$.  
   - **Back-action:** The board state collapses onto the eigenspace  
     $
     \Pi_{i,c_i} = \sum_{\mathbf{m}:\,\sum_{j\in\mathcal{N}(i)} m_j = c_i}
     \ket{\mathbf{m}}\!\bra{\mathbf{m}},
     $
     preserving superpositions only among configurations with the same local count.  
   - **Remarks:**  
     - All $C_i$ commute (being functions of commuting $Z_j$ operators), so the order of such measurements does not affect statistics, though it changes the post-measurement state.  
     - In a computational basis state, this reproduces the classical Minesweeper clue exactly.

2. **Weak measurement.**  
   Perform a gentle measurement of $C_i$ that only partially collapses the state.  
   - **Outcome:** A noisy scalar whose mean is \(\langle C_i\rangle\).  
   - **Back-action:** Reduces coherence between sectors with different $c_i$ values, but does not fully project the state.  
   - **Remarks:** Repeating the measurement reduces noise but accumulates disturbance; this allows for an adjustable trade-off between information gain and state preservation.

3. **Expectation-value readout (average count).**  
   Return the expectation value  
   $
   \langle C_i \rangle = \sum_{j\in\mathcal{N}(i)} \langle M_j \rangle
   = \sum_{j\in\mathcal{N}(i)} \Pr(\text{mine at } j),
   $
   a real number in $[0,|\mathcal{N}(i)|]$.  
   - **Information content:** Reveals only the **marginals** (sum of single-site mine probabilities) around $i$, without revealing correlations or which neighbors contribute.  
   - **Remarks:** In an idealized “oracle” version, this can be obtained without disturbing the state; in a physical setting, it requires repeated projective or weak measurements on identically prepared boards.

---

**Design trade-offs.**  
- **Granularity:** Projective readout gives exact integers; weak and expectation-value methods yield real numbers with varying precision.  
- **Collapse:** Projective readout collapses fully; weak measurement collapses partially; expectation-value readout can be modeled as non-destructive.  
- **Inference:** Projective readout provides strong local constraints immediately; expectation-value methods require combining data from many queries to reconstruct the board state.  
- **Difficulty knob:** Weak and expectation-value readouts allow tuning of noise, precision, and query budget to adjust game difficulty.


#### Allowed moves

In addition to querying a clue, the player can take actions that change the board state. In the quantum setting, these are defined as **operations** (unitaries or measurements) acting on the mine Hilbert space \(\mathcal{H}\) and, in some cases, on the classical explored-cells register \(S_e\).

We can group possible moves into the following categories:

1. **Classical-style reveal.**  
   - **Rule:** Select a cell \( i \) and perform a strong projective measurement of its mine qubit in the computational basis \(\{\ket{0},\ket{1}\}\).  
   - **Outcome:** Either “safe” (\(\ket{0}\)) or “mine” (\(\ket{1}\)); in the latter case, the game ends immediately.  
   - **Back-action:** Fully collapses the \(i\)-th qubit to an eigenstate of \(Z_i\), disentangling it from the rest of the board.

2. **Quantum exploration moves.**  
   These allow the player to manipulate the quantum state before or instead of measuring. Examples include:
   - **Single-qubit gates:**  
     Apply \( H_i \) (Hadamard) to create superpositions, \( X_i \) to flip mine/safe, or arbitrary \( R_{\hat{n}}(\theta) \) rotations.  
   - **Entangling gates:**  
     Apply \( \mathrm{CNOT}_{i\to j} \), CZ, or other two-qubit gates between neighboring cells. This can spread or concentrate quantum correlations, potentially aiding or confusing deduction.  
   - **Swap/Permutation operations:**  
     Exchange the quantum states of two cells (\(\mathrm{SWAP}_{ij}\)) without revealing their contents.

3. **Adaptive measurements.**  
   Measurements in bases other than the computational \(Z\)-basis, e.g. \(X\)- or \(Y\)-basis.  
   - **Rule:** Choose a basis defined by a local unitary \(U\) before measuring.  
   - **Motivation:** Non-\(Z\) measurements can reveal phase information in superpositions of mine configurations—information absent in the classical game.

#### Allowed moves

We allow exactly two classes of moves.

1. **Probe \((i)\)** — *reveal cell \( i \) and its clue*  
   A probe both checks whether \( i \) is a mine and (if safe) reveals the clue at \( i \).
   - **Mine check (loss condition).** Measure \( Z_i \) projectively.  
     - Outcome \(+1\) (state \( \ket{0}_i \)): \( i \) is safe — continue to clue readout.  
     - Outcome \(-1\) (state \( \ket{1}_i \)): \( i \) is a mine — **game over (loss)**.
   - **Clue readout (only if safe).** Query the clue operator
     \[
     C_i \;=\; \sum_{j\in\mathcal{N}(i)} M_j
     \;=\; \tfrac{1}{2}\sum_{j\in\mathcal{N}(i)}(\mathbb{I}_2 - Z_j)
     \]
     using one of the following models (chosen as a game parameter):
     - **Projective readout (exact count).** Measure \( C_i \) in its eigenbasis; reveal the integer \( c_i\in\{0,\dots,|\mathcal{N}(i)|\} \). Post‑measurement state collapses onto the \( c_i \) eigenspace.  
     - **Weak measurement.** Implement a gentle measurement of \( C_i \) (e.g., Gaussian‑pointer model). Reveal a real‑valued noisy outcome \( x \) with \( \mathbb{E}[x]\propto \langle C_i\rangle \); partial dephasing in the \( C_i \) basis occurs.  
     - **Expectation‑value readout.** Reveal \( \langle C_i\rangle = \sum_{j\in\mathcal{N}(i)} \langle M_j\rangle \) (ideal, non‑destructive oracle interpretation or many‑shot estimate on identically prepared boards).
   - **Bookkeeping.** Set the explored bit \( S_e[i]\gets 1 \) when the clue is revealed (safe case).

2. **Quantum move** — *apply gates to manipulate the board state*  
   These moves act unitarily on the mine Hilbert space \( \mathcal{H} \) without changing \( S_e \).
   - **Single‑qubit gates (on any cell \( i \)).**  
     Allowed set \( \mathcal{G}_1 \) (choose per variant), e.g.
     \[
     \{X_i,\, Z_i,\, H_i,\, S_i,\, R_x^{(i)}(\theta),\, R_z^{(i)}(\phi)\}.
     \]
   - **Two‑qubit gates (on neighboring cells \( i\sim j \)).**  
     Allowed set \( \mathcal{G}_2 \) (nearest‑neighbor by default), e.g.
     \[
     \{\mathrm{CNOT}_{i\to j},\, \mathrm{CZ}_{ij},\, \mathrm{SWAP}_{ij},\, \mathrm{iSWAP}_{ij}\}.
     \]
   - **Locality / depth constraints (game knobs).**  
     Optionally restrict gates to grid‑adjacent pairs, impose a per‑turn gate budget, or a total circuit‑depth cap to control difficulty and prevent trivializing strategies.

**Remarks.**  
- **Commutation & order effects.** Probes (mine check + clue) are diagonal in the \( Z \) basis, while quantum moves generally are not; therefore the order of gates and probes matters.  
- **Classical limit.** Disallowing quantum moves and using only projective clue readout reduces the game to classical Minesweeper rules.  
- **Strategy space.** Quantum moves allow state preparation (e.g., creating or removing entanglement) prior to probing, enabling interference‑based inference or, conversely, adversarial puzzle design.

### Winning and loss conditions

The loss condition is universal: if $\exist i \in S_e(i)=1 s.t. <Z_i> = 1$ (an explored cell has a mine) the game terminate with a loss.

For the winning condition we have two options:

- *Survival mode* : You need to explore all the cell where $\langle Z_i \rangle = 0$ 
- *Clearing mode* : You need to manipulate the board such that $\langle Z_i \rangle = 0$ in each cell (clear the board)

### Consistent game rule set

A ruleset can be identified by the following:
- A *board preparation rule* 
- A *clue mechanism* 
- A *quantum manipolation ruleset*
- A *winning condition* 





---

**Remarks on move design.**  
- **Commutativity:** Classical reveal and clue measurements commute (all are diagonal in the \(Z\)-basis), but quantum gates generally do not, so the order of operations matters.  
- **Strategy space:** Allowing coherent gates between queries opens a much larger strategic space, where players can engineer interference patterns to extract information more efficiently than classically possible.  
- **Pedagogical tuning:** Restricting moves to projective \(Z\)-basis reveals yields a classical-like game; adding gates and non-\(Z\) measurements turns it into a sandbox for teaching basic to advanced quantum operations.



References
----------

-   [Minesweeper is NP
    Complete](https://link.springer.com/article/10.1007/BF03025367)
-   [Standard model physics and the digital quantum revolution: thoughts
    about the interface](https://doi.org/10.1088/1361-6633/ac58a4) 
