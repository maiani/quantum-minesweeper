**Please help our research by compiling the 
  <a href="https://forms.gle/RxeVbhvDuq8vciWk9" style="color:red">
    Post Game Survey
  </a> 
  after you played some times!**

## Game rules

**Goal**: Defuse all mines by bringing every cell to the |0> state. If you measure a cell and observe |1>, you lose.

**Overview**: Each cell is a qubit (quantum bit): it may be a mine |1>, empty |0>, or in a superposition. Use measurements to reveal the expected number of mines in neighbouring cells, or apply gates to change the quantum states of the unrevealed cells.

---

### Controls

- **Measure**: collapses a cell to |0> (no mine) or |1> (mine). If you observe |1>, you lose. If you observe |0>, the cell becomes **revealed** and displays the expected number of mines in the neighbouring cells.

- **Apply gate**: manipulates the quantum state of a cell without revealing it. (See the help pages for a description of the different gates you can use.)

### Levels

- **Classical (Level 0)**

    - Start here to refresh your memory. Here, mines behave just like in the traditional Minesweeper game.

- **Quantum (Level 1)**

    - Cells can be in a **superposition state**, meaning that there is a 0.5 probability of being occupied or unoccupied by a mine. If you measure a cell in a superposition, you have a 0.5 probability of losing.
    - There are two kinds of actions: **measurements** and **gates**.
    - If you measure a cell, you either lose (if you find a mine), or reveal the expected number of mines in neighbouring cells.
    - Since you will not know the quantum state of the unrevealed cells, you will need to apply gates to see how it changes the numbers in the neighbouring revealed cells.

- **Quantum (Level 2+)**

    - At higher levels, mines can be **entangled**.
    - **Entanglement** means that the state of two (or more) cells can be **correlated**. For example, a mine can be in a superposition of being in either one cell or another cell. So knowing the state of one tells you about the other.
    - This makes clearing the board trickier, since measuring one cell can change the state of another!
    - In these levels, you unlock **two-qubit** gates, which you use on two cells at a time. You will need to apply these gates to disentangle the entangled cells before defusing the mines.
    - Higher levels of entanglement (Level 3 and 4) means that more than two cells can be entangled at the start of the round.

- **Sandbox**

    - A playground where you can freely try out gates and see what they do to the board, without worrying about winning or losing.

---

The best way to learn is to **start simple** (classical mines), and then experiment step-by-step with different gates in Sandbox mode. You'll build intuition about how quantum mines behave and how to defuse them.
