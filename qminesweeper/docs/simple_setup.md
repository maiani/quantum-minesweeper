## Game Rules

Quantum Minesweeper starts from the rules of the **classic Minesweeper**:  
- The board hides a set of **mines**.  
- Each cell, when revealed, shows a **number** telling you how many mines are in the neighboring cells.  
- In the classical version, you win if you avoid clicking on mines and identify all their locations.

### The Quantum Twist
In the **quantum version**, mines are no longer fixed.  
- A mine is represented by a **qubit** (a quantum bit).  
- Qubits can be in **superpositions** which means a cell can be both occupied and unoccupied by a mine at the same time.  
- To win, you don’t just identify mines — you must **defuse them** by applying the right **quantum gates**.

---

### How to Play
- **Start with the classical version** (Level 0) to refresh your memory. Here, mines behave just like in the normal Minesweeper you already know.  
- The **Sandbox mode** is always available: it’s a playground where you can freely try out gates and see what they do to the board, without worrying about winning or losing.  

#### Superposition bombs
- At Level 1, each cell can be in a superposition state, that means that may have 50% probability of being occupied and unoccupied. 
- If you measure a cell with a superposition bomb, you have 50% of probability of losing and 50% of winning. 
- But do not dispear, At this level, you unlock the first category of quantum moves **single qubit gates** (gates)
- Gates let you change the state of qubits and gradually “clear” mines.  
- Your objective is to remove the mine by appling the right combination of gates.

#### Entangled Mines
At higher levels, mines may be **entangled**.  
- Entanglement means two or more mines are **linked together**: their states are correlated, no matter which cell you open first.  
- Intuitively, think of it as mines that “share a fuse” — cutting one affects the others.  
- This makes clearing the board trickier, because defusing a single bomb might require acting on its entangled partner too.  

---

The best way to learn is to **start simple** (classic mines), then experiment step by step with gates in Sandbox. 
You’ll build intuition about how quantum mines behave and how to defuse them.  
