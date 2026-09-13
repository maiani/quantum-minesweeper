## How to play

**Goal:** leave no mines on the board. From Level 1 up that means bringing every
cell to zero chance of holding a mine — not working out where the mines are, but
removing the possibility that there are any. (Level 0 is ordinary Minesweeper:
there you win by opening every safe cell.)

**What makes it quantum:** a cell is not a fixed mine or a fixed blank. It can
hold both possibilities at once, and it settles on one only when you measure it.
Until then it has a *probability* of being a mine, and that probability is
something you can change.

---

### Your moves

- **Measure** opens a cell. If it is safe, it shows how many mines to expect
  around it. If it is a mine, you lose. A cell that is half likely to be a mine
  adds 0.5 to its neighbours' numbers, so clues are often fractions.

- **Gates** change a cell *without* opening it. This is how you lower a cell's
  chance of being a mine instead of gambling on it. Gates work only on cells you
  have not opened yet: an opened cell has already settled, and nothing moves it.

- **Pin** marks a cell you suspect. It is a note to yourself and changes nothing
  about the board.

Open the **❓** panel and hover over anything on the game screen — a counter, a
gate button, the probe — to read what it does.

---

### Levels

- **Level 0 — Classical**

    Ordinary Minesweeper. Mines are fixed, and you win by opening every safe
    cell. Start here to warm up.

- **Level 1 — Superposition**

    A cell can now be in **superposition**: an even chance of mine or no mine.
    You can still measure it, but that is now a coin flip, so measuring is a
    gamble rather than a way to make progress. Gates are the safe way forward:
    apply one to an unopened cell and watch the clue numbers around it move.

- **Levels 2 to 4 — Entanglement**

    Cells can now be **entangled**: their outcomes are linked, so learning about
    one tells you something about another. A single mine may be spread across
    two cells, in a superposition of sitting in either one. Measuring one cell
    can then change the other, which makes the board harder to clear.

    These levels give you **two-qubit gates**, which act on two cells at once.
    Use them to break the links before dealing with the mines. Levels 3 and 4
    entangle three and four cells at a time.

- **Sandbox**

    No winning, no losing. Try gates and watch what they do.

---

Start at Level 0 or 1, then use Sandbox to test one gate at a time. Watching a
single gate move a single clue is the quickest way to learn what it does.
