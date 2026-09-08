<p align="center">
  <img src="qminesweeper/static/icons/icon-512.png" alt="Quantum Minesweeper" width="128">
</p>

<h1 align="center">Quantum Minesweeper</h1>

<p align="center">
  <a href="https://github.com/maiani/quantum-minesweeper/actions/workflows/tests.yml"><img src="https://github.com/maiani/quantum-minesweeper/actions/workflows/tests.yml/badge.svg?branch=main" alt="CI status"></a>
  <a href="https://github.com/maiani/quantum-minesweeper/releases"><img src="https://img.shields.io/github/v/tag/maiani/quantum-minesweeper?label=release&sort=semver" alt="Latest release"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
</p>

Quantum Minesweeper is a quantum twist on the classic game of Minesweeper.
Instead of a fixed hidden layout, each cell is a qubit and a mine is the
Z-basis outcome $|1\rangle$. Measure qubits or apply Clifford gates to identify
or clear the quantum mines. In Clear mode, clearing means making every mine
outcome impossible.

---

## Features

- **Shared game with multiple runtimes**
  - **TUI** powered by Rich
  - **Server Web UI** powered by FastAPI and Uvicorn
  - **Browser-only PWA** powered by Pyodide, with no application server
- **Multiple backends** (selected with `--backend` or `QMS_BACKEND`)
  - **PurePy** — NumPy stabilizer tableau with no native extension dependency
    (default for local and static-browser runs, including Pyodide)
  - **Stim** — optional fast C++ stabilizer simulator (default for deployed server runs)
  - **Qiskit** — optional stabilizer simulator via Qiskit
- **Game modes**
  - **Classical** — standard Minesweeper rules with $|1\rangle$ mines
  - **Identify** — identify deterministic mines and explore all safe regions
  - **Clear** — apply gates to drive all mine probabilities to zero
  - **Sandbox** — no win condition; experiment freely with gates
- **Moves**
  - Classical: **Measure (M)**, **Pin (P)**
  - 1-qubit gates: **X, Y, Z, H, S, Sdg, SX, SXdg, SY, SYdg**
  - 2-qubit gates: **CX, CY, CZ, SWAP**
- **Web entanglement probes**
  - Click cells, or drag a rectangle across the board, to inspect the
    entanglement between an area and the rest of the board.
  - Advanced Setup chooses the number of regions: 0 for none, 1 for one area
    against the rest, 2 to compare two areas by mutual information. Simple
    Setup turns them on wherever entanglement can appear: Level 2 and above,
    and Sandbox.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/maiani/quantum-minesweeper.git
cd quantum-minesweeper

# Copy the example settings
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
- `QMS_ENABLE_ENTANGLEMENT_PROBES` - whether the entanglement probe exists in
  this deployment (default on). How many regions a game gets is a separate
  per-game choice in Setup, not a deployment setting
- `QMS_BASE_URL` can be set for absolute paths.
  
Create a `.env` from the supplied `.env_example` in local development.


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

### Browser-only PWA

Run the game entirely in the browser, on Pyodide and the PurePy backend:

```bash
pixi run browser-serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The static build does not need FastAPI, a database, or Cloud Run while you
play. It saves the current game in `localStorage`, so a reload restores the
in-progress board. The bundle also includes a manifest and service worker for
installation and offline use after its initial successful load.

### Docker
Build and run locally with

```bash
pixi run docker-run
```

---

## Development & Testing

Create the reproducible development environment and run the checks through it:

```bash
pixi install
pixi run pre-commit install
pixi run check
```

Pixi installs Python, the editable package with all development and optional
simulator dependencies, Node.js, and the SVG tooling used to regenerate PWA
icons. Exact versions are recorded in `pixi.lock`. `pixi run check` runs Ruff,
pytest, and syntax checks over every frontend JavaScript file.

If Pixi is unavailable, a conventional editable install remains supported:

```bash
pip install -e ".[dev]"
pytest
python -m ruff check qminesweeper tests scripts
```

The test suite exercises all installed simulator backends.

Run `pixi task list` to list all development, packaging, browser, Docker, and
deployment commands. Their implementation remains in Python modules and the
scripts under `scripts/`.

Project design and active work are documented in
[`docs/architecture.md`](docs/architecture.md) and
[`docs/roadmap.md`](docs/roadmap.md).

---
## Gameplay Notes

- Classical mode matches standard Minesweeper: mines are fixed $|1\rangle$
  states and clues sum over neighbors.
- Quantum modes use stabilizer states:
  - Identify: measure to reveal deterministically safe cells.
  - Clear: apply gates (and measurements) to drive each cell's Z-basis mine probability to ~0.

Two counters sit above the board. The ⟨💣⟩ counter is the expected number of
mines:

$$
\langle Mines \rangle=\sum_i p_i 
$$

where $p_i$ is the current Z-basis mine probability of cell $i$. The counter
marked with two interlocked rings is the sum of the single-cell entropies, in
bits. The icons stand alone in the interface; the help pane names each counter
and its unit.

Use `Sandbox` to learn gate effects: see how $H$, $S$, $CX$, and other
Clifford gates change clues and probabilities without a win condition.

Entanglement probes are available in all web game modes when the rule is
enabled. Selecting an area $A$ reports its entropy $S(A)$ against the rest of
the board, in bits. Selection is a read-only simulator diagnostic: it does not
measure cells or change the state. Selected cells can be disconnected, and
revealed cells can be included without changing their gate restrictions.

For independent Bell pairs, $S(A)$ counts pairs split by the selection. One
member of a Bell pair gives 1 bit; selecting both gives 0. Zero means no
entanglement with the outside, not necessarily no entanglement inside the area.

The optional two-area mode compares disjoint areas $A$ and $B$ using mutual
information $I(A:B)=S(A)+S(B)-S(A\cup B)$. This measures total shared
information, including classical and quantum correlations. Two halves of a
Bell pair share 2 bits of mutual information; cells from independent pairs
share 0. Multipartite states need not follow a pair-count interpretation.
The existing status counter is the sum of single-cell entropies, a different
quantity. All these diagnostics describe the current state conditioned on
recorded measurement outcomes.


## Authors
- Andrea Maiani
- Niklas Engelhardt Önne
- Jason Pye

## License
MIT License.  
(c) 2025-2026 Andrea Maiani and contributors.
