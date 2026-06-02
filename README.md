# Quantum Minesweeper

Quantum Minesweeper is a quantum twist on the classic game of Minesweeper.  
Instead of fixed mines, the board is prepared in **quantum states** (classical mines, product stabilizers, or entangled stabilizers).  
You interact with the board by **measuring qubits** or **applying quantum gates**, and you must **identify** or **clear** the "quantum mines." In Clear mode, clearing means making every mine outcome impossible.

---

## Features

- **Two interfaces**
  - **TUI** (Text UI) powered by `rich`
  - **Web UI** powered by **FastAPI** + **Uvicorn**
- **Multiple backends** (selected with `--backend` or `QMS_BACKEND`)
  - **PurePy** — pure-Python stabilizer tableau, no native deps (default for local/static browser runs; runs anywhere, incl. Pyodide)
  - **Stim** — optional fast C++ stabilizer simulator (default for deployed server runs)
  - **Qiskit** — optional stabilizer simulator via Qiskit
- **Game modes**
  - **Classical** - standard Minesweeper rules with |1⟩ mines
  - **Identify** - identify deterministic mines and explore all safe regions
  - **Clear** - apply gates to drive all mine probabilities to ~0
  - **Sandbox** - no win condition; experiment freely with gates
- **Moves**
  - Classical: **Measure (M)**, **Pin (P)**
  - 1-qubit gates: **X, Y, Z, H, S, Sdg, SX, SXdg, SY, SYdg**
  - 2-qubit gates: **CX, CY, CZ, SWAP**

---

## Installation

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
python -m pip install .
```
---

## Running

### Configuration 

Configuration is centralized with Pydantic Settings and loaded from environment variables (and .env in dev).

Common flags:
- `QMS_BACKEND` - simulator backend: `purepy`, `stim`, or `qiskit`. Local config defaults to `purepy`; `scripts/deploy.sh` defaults deployed server runs to `stim`.
- `QMS_ENABLE_AUTH`  - enable HTTP basic auth
- `QMS_USER` / `QMS_PASS` - credentials for basic auth
- `QMS_ADMIN_PASS` - admin dashboard password; leave unset to disable admin routes
- `QMS_ENABLE_HELP` - render the in-app Help sidebar toggle
- `QMS_ENABLE_TUTORIAL` / `QMS_TUTORIAL_URL` - show a Tutorial link
- `QMS_ENABLE_SURVEY` / `QMS_SURVEY_URL` - show a Survey link
- `QMS_BASE_URL` can be set for absolute paths.
  
Create a `.env` (or use `.env.example`) in local dev.


### Textual Interface (TUI)
Launch the text UI:
```bash
python -m qminesweeper tui
```

Default backend is **PurePy**. You can also install and select Stim or Qiskit:
```bash
python -m qminesweeper tui --backend purepy
python -m pip install ".[stim]"
python -m qminesweeper tui --backend stim
python -m pip install ".[qiskit]"
python -m qminesweeper tui --backend qiskit
```

### Web Interface
Launch the web interface with:
```bash
python -m qminesweeper webui --port 8080
```

Then open your browser at: [http://127.0.0.1:8080](http://127.0.0.1:8080)

Local web UI runs use the configured backend, which defaults to **PurePy** for a
plain install. The Docker/Cloud Run deployment installs the Stim extra and
defaults `QMS_BACKEND` to **Stim** unless you override it.

### Browser-only build
Build a static version that runs the game in the page with Pyodide and the
pure-Python backend:

```bash
make browser
make browser-serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The static build does
not need FastAPI, a database, or Cloud Run while you play. It saves the current
browser game in `localStorage`, so a reload restores the in-progress board.

### Docker
Build and run locally with

```bash
make run
```

---

## Development & Testing

You can install the package including the development dependencies in editable mode as 

```bash
pip install -e ".[dev]"
pre-commit install
```

We run tests with [pytest](https://pytest.org/):
```bash
pytest tests/
```

---
## Gameplay Notes

- Classical mode matches standard Minesweeper: mines are fixed |1⟩ states; clues sum over neighbors.
- Quantum modes use stabilizer states:
  - Identify: measure to reveal deterministically safe cells 
  - Clear: apply gates (and measurements) to drive each cell's Z-basis mine probability to ~0.

The status bar shows the expected number of mines:

$$
\langle Mines \rangle=\sum_i p_i 
$$

where $p_i$ is the current Z-basis mine probability of cell $i$.

Use `Sandbox` to learn gate effects: see how $H$, $S$, $CX$, etc. change clues and probabilities without a win condition


## Authors
- Andrea Maiani
- Niklas Engelhardt Önne
- Jason Pye

## License
MIT License.  
(c) 2025-2026 Andrea Maiani and contributors.
