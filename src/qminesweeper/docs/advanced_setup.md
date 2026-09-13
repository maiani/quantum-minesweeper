## Setup options

Simple Setup fills all of these in for you. Change them here to build a board
the levels do not offer.

#### 1. Board size

Rows $R$ and columns $C$. The board is $N = R \times C$ cells, one qubit each.

#### 2. Mines and entanglement level

**Mines** $B$ is how many mines are placed. **Entanglement level** controls how
they are prepared:

- **Level 0** — ordinary fixed mines: every cell is definitely $|0\rangle$ or
  $|1\rangle$.
- **Level 1** — each mine is an independent single cell in superposition, such
  as $|+\rangle$ or $|i\rangle$.
- **Level $k$** — mines are prepared in random entangled states over groups of
  $k$ cells. Level 2 gives Bell-pair-like states, Level 3 GHZ-type states, and
  so on.

While you play, the number of mines on the board is an average rather than a
count:
$$
\langle \text{Mines} \rangle = \sum_i p_i,
\qquad
p_i = \tfrac{1}{2}\left(1 - \langle Z_i \rangle\right),
$$
where $p_i$ is the probability that cell $i$ holds a mine.

#### 3. Win condition

- **Identify** — win by opening every currently safe cell without ever measuring
  a mine.
- **Clear** — win by driving every cell to mine probability zero. The mines are
  not hidden somewhere to be found: the goal is to make a mine outcome
  impossible.
- **Sandbox** — free exploration, with no win and no loss.

#### 4. Move set

Which operations you may use:

- **Classic** — measure (`M`) and pin (`P`) only.
- **One-qubit (core set)** — adds $X$, $Y$, $Z$, $H$, $S$, which is enough to
  defuse single-cell mines.
- **One-qubit (full set)** — adds $S^\dagger$, $\sqrt{X}$, $\sqrt{X}^\dagger$,
  $\sqrt{Y}$, $\sqrt{Y}^\dagger$, completing the single-qubit Clifford group.
- **Two-qubit** — adds $CX$ and $SWAP$ to the core set.
- **Two-qubit (extended)** — adds $CX$, $CY$, $CZ$ and $SWAP$ to the full set.

Either two-qubit set lets you create and undo entanglement yourself.

#### 5. Entanglement probe regions

How many regions the probe offers this game: **0** for none, **1** to weigh one
region against the rest of the board, or **2** to also compare two regions.
Simple Setup picks a count to suit the level; choosing here overrides it.

The probe only reads the state. It never measures a cell, applies a gate or
moves a pin, and it does not use up a move.

Region $A$ is reported as its entanglement entropy against the rest of the
board,
$$
S(A) = -\mathrm{Tr}\left(\rho_A \log_2 \rho_A\right),
$$
in bits. For independent Bell pairs this counts the pairs straddling the
region's boundary: selecting one member gives 1 bit, selecting both gives 0. A
product state such as $|+\rangle$ gives 0 even though its mine outcome is still
uncertain, and a reading of 0 does not rule out entanglement *inside* the
region.

With two regions, disjoint regions $A$ and $B$ also report their mutual
information
$$
I(A:B) = S(A) + S(B) - S(A \cup B),
$$
with $S(A)$, $S(B)$ and $S(A \cup B)$ shown alongside. This measures total
correlation, classical as well as quantum. A Bell pair split between the two
regions gives 2 bits, while cells from different pairs give 0. Take care beyond
two cells: in a three-cell GHZ state, two cells share 1 bit this way even
though their own two-cell state is not entangled. Do not read $I(A:B)$ as a
count of pairwise links.

Regions stay selected while you switch back to gates and measurement, so you can
compare a reading before and after a move. Opened cells may be selected, but
still cannot be targeted by gates. Every reading describes the board as it
stands, given the measurement outcomes so far.

This is not the linked-rings counter above the board, which adds up each cell's
own entanglement separately. The region count survives a reset, a new game with
the same settings, and a saved browser game; the cells you selected do not.
