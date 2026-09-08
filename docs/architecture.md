# Architecture

_Last reviewed: 2026-09-08_

This document records stable implementation boundaries, completed design
decisions, and constraints that hold indefinitely. Active work belongs in
[`roadmap.md`](roadmap.md), and release history in
[`../CHANGELOG.md`](../CHANGELOG.md).

## Core model

- Each board cell is one qubit.
- A mine is the Z-basis outcome $|1\rangle$.
- Mine probability is
  $p_i = \langle M_i\rangle = (1 - \langle Z_i\rangle) / 2$, where
  $M_i = (I - Z_i) / 2$.
- The implemented clue is the sum of neighboring Z-basis mine probabilities.
- The simulator model is stabilizer/Clifford: it supports superposition,
  measurement, gates, and entanglement while remaining efficiently simulable.
- `Identify`, `Clear`, and `Sandbox` are win-condition modes. Move sets are a
  separate setup choice.
- Clear-mode language stays explicit everywhere it appears: the goal is to make
  mine outcomes impossible, not to locate a fixed hidden layout.
- Pinning is a player annotation, not a quantum operation.
- Gates cannot target explored cells. Explored cells represent revealed
  classical information; transforming them would make the displayed state
  misleading and could turn a revealed safe cell into a mine.

## Runtime structure

Quantum Minesweeper is one product with three entry paths:

- The TUI uses `board`, `game`, and the selected simulator backend directly.
- Server mode uses FastAPI and Jinja, with game state computed on the server.
- Browser-only mode runs the same Python rules in Pyodide on `PurePyBackend`.

The server and browser modes share the game contract, renderer, templates,
styles, documentation, and terminology.

### Shared game contract

`qminesweeper/engine.py` is framework-free and Pyodide-safe. It owns:

- `serialize_game(board, game, game_id) -> dict`
- `Command` and `parse_command`
- `apply_command`
- setup validation and shared game construction

The serialized value is a lean game-state dictionary. Presentation and feature
flags do not belong in it. A parallel `GameView`/`CellView` model was considered
and removed because it duplicated existing state.

### Frontend boundary

- `qminesweeper/static/scripts/render.js` is the single game renderer.
- `HttpEngine` sends commands to the existing FastAPI routes in server mode.
- `PyodideEngine` sends commands to `BrowserSession` in browser-only mode.
- Symbols, labels, colours, and visible tool choices live in JavaScript.
- Feature flags travel in a separate application-config object.
- Shared Jinja templates remain the visible-page source of truth. The static
  build renders them at build time with only small browser-specific hooks.

There is no separate `/api/*` game-state namespace and no second browser
frontend.

### Footer logos

Acknowledgement logos live in the shared footer template. Nordita's is inlined
from `templates/_nordita_logo.svg` rather than referenced as an image: it is a
single-colour SVG painted in `currentColor`, so one asset follows both themes
(a referenced `<img>` cannot see page CSS). It was rebuilt from
`static/nordita.svg` — the official vector logo — by keeping the mark's petal
paths, subtracting the middle lens through a mask instead of painting it white,
and outlining the "NORDITA" wordmark from Montserrat Medium, Nordita's brand
font, so no webfont is needed at render time. Cap height, tracking, and the
mark box were fitted to the official raster logo. WINQ's logo stays a small
`<img>`: it is multi-colour brand artwork that must not be recoloured.

Changing either logo is an asset change, not a layout change. Colour belongs in
`base.css`; the SVG geometry should be left alone.

## Simulator backends

`QuantumBackend` abstracts quantum simulation, not deployment mode. Gate arity
is declared once through `ONE_QUBIT_GATES` and `TWO_QUBIT_GATES` in
`quantum_backend.py`.

- `PurePyBackend` is the default for local installs and the browser build. It is
  a NumPy stabilizer tableau with no native extension dependency.
- `StimBackend` is optional and is the default in Docker/server deployment.
- `QiskitBackend` is optional and provides an additional parity target.

Optional backends are imported lazily. Backend parity tests cover all installed
implementations.

The three implementations and their numerical parity tests are deliberately
independent. Their duplication is the parity check; do not consolidate them
behind a shared numerical core.

## Browser-only distribution

`qminesweeper/browser.py` owns an in-memory `BrowserSession`. Setup, move,
reset, and new-same operations all return the shared serialized state.

The browser session can export and import a versioned snapshot containing setup
parameters, game status, preparation circuit, clue and flood-fill settings,
exploration and pin state, measured outcomes, and the PurePy tableau. The web
frontend persists this snapshot in `localStorage`.

`scripts/build_browser.py` produces `dist/` with:

- static CSS, JavaScript, help, and icon assets;
- the pure Python modules loaded by Pyodide;
- setup and About pages rendered from shared templates;
- a PWA manifest and content-fingerprinted service worker.

The service worker uses network-first caching for same-origin application files
and cache-first behavior for versioned cross-origin Pyodide assets. The static
bundle requires no FastAPI server, database, or Cloud Run deployment.

## Packaging outputs

The wheel, source distribution, browser `dist/`, and Docker image are separate
artifacts that stay isolated from one another:

- `pixi run package` writes the wheel and source distribution to
  `build/packages`, keeping them out of the browser bundle's `dist/`.
- `scripts/build_browser.py` owns `dist/` and builds it from the package source
  tree rather than from a built wheel.
- The Docker image builds and installs its own wheel in a builder stage rather
  than consuming a host `build/packages` or `dist/`.

Each artifact therefore builds from source, and none assumes another has been
produced first.

## Completed browser milestones

1. A pure-Python stabilizer backend with Stim/Qiskit parity coverage.
2. A shared JavaScript renderer replacing server-rendered game controls.
3. A framework-free command and serialization contract.
4. No-reload server moves returning serialized state.
5. An in-browser Pyodide session using the same rules.
6. Versioned browser save and restore.
7. A static Jinja-based build with shared setup and About pages.
8. PWA assets, install metadata, and a content-fingerprinted service worker.

## Performance boundary

Whole-board observables, especially `expected_mines()` and
`entanglement_score()`, are the main PurePy render cost. Optimize only from
measured browser evidence. Preferred mitigations are backend-agnostic
expectation caching, invalidation after measurements and gates, and lazy or
throttled entanglement display before reducing supported board sizes.

## Deliberately deferred features

- Region bipartite-entropy probes are advanced diagnostics, not part of the
  browser critical path.
- Basis-changing clues are an exploratory Sandbox teaching feature. Identify
  and Clear semantics remain Z-basis unless a separate ruleset is designed, and
  the material must say that clue basis changes the diagnostic, not the
  definition of a mine.
- Circuit history, challenges, scoring, and RL tooling should build on the
  shared engine contract and its deterministic seeds rather than introduce
  parallel state models.
