# Quantum Minesweeper

Quantum Minesweeper is a quantum twist on the classic game of Minesweeper.  
Instead of fixed mines, the board is prepared in **quantum states** (classical mines, product stabilizers, or entangled stabilizers).  
You interact with the board by **measuring qubits** or **applying quantum gates**, and you must **identify** or **clear** the “quantum mines.”

---

## ✨ Features

- **Two interfaces**
  - **TUI** (Text UI) powered by `rich`
  - **Web UI** powered by **FastAPI** + **Uvicorn**
- **Multiple backends**
  - **Stim** (fast stabilizer simulator, default)
  - **Qiskit** (general Clifford support)
- **Game modes**
  - **Classical** — standard Minesweeper rules with |1⟩ mines
  - **Identify** — identify deterministic mines and explore all safe regions
  - **Clear** — apply gates to drive all mine probabilities to ~0
  - **Sandbox** — no win condition; experiment freely with gates
- **Moves**
  - Classical: **Measure (M)**, **Pin (P)**
  - 1-qubit gates: **X, Y, Z, H, S, Sdg, SX, SXdg, SY, SYdg**
  - 2-qubit gates: **CX, CY, CZ, SWAP**

---

## 🧰 Installation

```bash
# Clone the repository
git clone https://github.com/maiani/quantum-minesweeper.git
cd quantum-minesweeper

# Copy the setting
cp .env_example .env

# Create and activate a virtual environment 
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install the package
python -m pip install -U pip
```
---

## ▶️ Running

### 🔧 Configuration 

Configuration is centralized with Pydantic Settings and loaded from environment variables (and .env in dev).

Common flags:
- `QMS_ENABLE_AUTH` (default: 1) — enable HTTP basic auth
- `QMS_USER` / `QMS_PASS` — credentials for basic auth
- `QMS_ENABLE_HELP` — render the in-app Help sidebar toggle
- `QMS_ENABLE_TUTORIAL`, `QMS_TUTORIAL_URL` — show a Tutorial link
- `QMS_BASE_URL` can be set for absolute pahts.
  
Create a `.env` (or use `.env.example`) in local dev.


### Textual Interface (TUI)
Launch the text UI:
```bash
python -m qminesweeper tui --backend stim
```

Default backend is **Stim** (fast).  You can also use Qiskit:  
```bash
python -m qminesweeper tui --backend qiskit
```

### Web Interface
Launch the web interface with:
```bash
python -m qminesweeper web --port 8080
```

Then open your browser at: [http://127.0.0.1:8080](http://127.0.0.1:8080)

### 🐳 Docker
Build and run locally with

```bash
make run
```

## 🎮 Controls & Commands

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

## 🧪 Development & Testing

You can install the package including the development dependencies in editable mode as 

```bash
pip install -e ".[dev]"
pre-commit install
```

We run tests with [pytest](https://pytest.org/):
```bash
pytest tests/
```


## Project structure:
```
qminesweeper/
  __main__.py           # Typer CLI: tui, webui
  webapp.py             # FastAPI app, routes & templates
  settings.py           # Pydantic BaseSettings (feature flags, auth)
  auth.py               # Basic auth middleware using settings
  board.py              # Board mechanics (state, clues, flood fill)
  game.py               # Rules engine (moves, win/lose)
  quantum_backend.py    # Backend abstraction
  stim_backend.py       # Stim implementation
  qiskit_backend.py     # Qiskit implementation
  logging_config.py     # Uniform logging style
  templates/            # Jinja2 templates (base, game, setup, footer)
  static/               # CSS, JS (theme), favicon
  docs/                 # Markdown docs rendered in UI (help/explanations)
tests/*                 # Unit tests
scripts/*               # Build scripts
```

---
## 🧠 Gameplay Notes

- Classical mode matches standard Minesweeper: mines are fixed |1⟩ states; clues sum over neighbors.
- Quantum modes use stabilizer states:
  - Identify: measure to reveal deterministically safe cells 
  - Clear: apply gates (and measurements) to drive each cell’s Z-bomb probability to ~0.

The status bar shows the expected number of mines:

$$
\langle Mines \rangle=\sum_i p_i 
$$

where $p_i$ is the current Z-basis bomb probability of cell $i$.

Use `Sandbox` to learn gate effects: see how $H$, $S$, $CX$, etc. change clues and probabilities without a win condition

---

## Ideas for the Future
- New move: draw a line on the board and return the **bipartite entanglement entropy**.  
  Could the player use entanglement information strategically?
- **Change clue basis**: allow switching from Z to X or Y basis for different perspectives on the bombs.
- **RL Agent**: integrate with Gymnasium/OpenAI Gym for reinforcement learning experiments.
- **PWA support**: package the web interface as a Progressive Web App for desktop/mobile play.

---


## Authors
- Andrea Maiani [andreamaian@su.se]

## License
MIT License.  
(c) 2025 Andrea Maiani.
