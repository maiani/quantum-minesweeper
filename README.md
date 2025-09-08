# Quantum Minesweeper

Quantum Minesweeper is a quantum twist on the classic game of Minesweeper.  
Instead of fixed mines, the board is prepared in quantum states (classical bombs, product stabilizers, or entangled stabilizers).  
The player interacts with the board by measuring qubits or applying quantum gates, and must identify or clear the “quantum bombs.”

---

## Features
- **Two interfaces**: 
  - Text-based interface (TUI) using [Rich](https://github.com/Textualize/rich).
  - Web-based interface (Flask, FastAPI in progress).
- **Multiple backends**: 
  - [Stim](https://github.com/quantumlib/Stim) (fast stabilizer simulator, default).
  - [Qiskit](https://qiskit.org/) (more general Clifford support).
- **Game modes**:
  - **Classical**: Standard Minesweeper rules with |1⟩ bombs.
  - **Quantum Identify**: Identify deterministic bombs and explore all safe regions.
  - **Quantum Clear**: Apply gates to clear all bomb probability.
- **Quantum moves**:
  - Single-qubit gates: X, Y, Z, H, S, …  
  - Two-qubit gates: CX, CY, CZ, SWAP.  
  - Classical actions: Measure, Pin.

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/QuantumMinesweeper.git
   cd QuantumMinesweeper
   ```

2. Create a conda environment:
   ```bash
   conda env create
   ```

   The default environment name is `qminesweeper`.

3. Activate the environment:
   ```bash
   conda activate qminesweeper
   ```

---

## Running Quantum Minesweeper

### Textual Interface (TUI)
Launch the text UI:
```bash
python -m qminesweeper tui --backend stim
```

- Default backend is **Stim** (fast).  
- You can also use Qiskit:
  ```bash
  python -m qminesweeper tui --backend qiskit
  ```

### Web Interface
Launch the web interface:
```bash
python -m qminesweeper web --port 5000
```

Then open your browser at: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Controls

### In the TUI
- **Measure**: `M 3,4` or just `3,4`
- **Pin**: `P 3,4`
- **Apply gate (single qubit)**: `X 2,2` `H 4,5` …
- **Apply gate (two qubits)**: `CX 1,1 2,1`, `SWAP 2,3 2,4`
- **Reset board**: `R`
- **New game (new rules)**: `N`
- **Quit**: `Q`

### In the Web UI
Click on tiles to measure or use toolbar buttons to apply gates/pins.  
Right-click pins a cell.

---

## Development & Testing

Run tests with [pytest](https://pytest.org/):
```bash
pytest tests/
```

Project structure:
```
src/
  quantum_board.py    # Core game logic
  quantum_backend.py  # Backend abstraction
  stim_backend.py     # Stim backend
  qiskit_backend.py   # Qiskit backend
  textUI.py           # TUI runner
  webapp.py           # Flask web app
tests/
  test_board_init.py  # Unit tests
```

---

## Ideas for the Future
- New move: draw a line on the board and return the **bipartite entanglement entropy**.  
  Could the player use entanglement information strategically?
- **Change clue basis**: allow switching from Z to X or Y basis for different perspectives on the bombs.
- **Progressive entanglement levels**: difficulty tuned by preparing stabilizer states with higher-body entanglement (product states → Bell pairs → GHZ).
- **RL Agent**: integrate with Gymnasium/OpenAI Gym for reinforcement learning experiments.
- **PWA support**: package the web interface as a Progressive Web App for desktop/mobile play.

---

## License
MIT License.  
(c) 2025 Quantum Minesweeper Authors.
