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
- Browser-only mode runs the same Python rules in Pyodide on `ChppyBackend`.

The server and browser modes share the game contract, renderer, templates,
styles, documentation, and terminology.

### Shared game contract

`src/qminesweeper/engine.py` is framework-free and Pyodide-safe. It owns:

- `serialize_game(board, game, game_id) -> dict`
- `Command` and `parse_command`
- `apply_command`
- setup validation and shared game construction

The serialized value is a lean game-state dictionary. Presentation and feature
flags do not belong in it. A parallel `GameView`/`CellView` model was considered
and removed because it duplicated existing state.

### Frontend boundary

- `src/qminesweeper/static/scripts/render.js` is the single game renderer.
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

- `ChppyBackend` is the default for local installs and the browser build. It is
  a NumPy stabilizer tableau with no native extension dependency.
- `StimBackend` is optional and is the default in Docker/server deployment.
- `QiskitBackend` is optional and provides an additional parity target.

Optional backends are imported lazily. Backend parity tests cover all installed
implementations.

The three implementations and their numerical parity tests are deliberately
independent. Their duplication is the parity check; do not consolidate them
behind a shared numerical core.

`src/chppy/` is an independent project vendored here rather than a component of
this application, kept ready to branch out into its own repository.
`ChppyBackend` is the sole adapter connecting it to the game contracts, and
absorbs any mismatch. That boundary is why the package keeps its own copies of
the gate-arity sets and the subset validator instead of importing the shared
definitions. `AGENTS.md` owns the rule to follow when changing it.

### Seeded sampling is per-backend

`QuantumBackend.random_clifford_circuit` accepts a `seed`, but the keyword is
best-effort and every backend documents its own behaviour. A seed is not a
portable board identifier.

- `ChppyBackend` honours it, with a generator independent of the global NumPy
  stream that unseeded calls use. Its docstring documents how the two relate.
- `QiskitBackend` honours it, via `random_clifford(k, seed=...)`.
- `StimBackend` ignores it: `stim.Tableau.random` exposes no seeding parameter.

A backend that cannot seed must accept and ignore the keyword rather than
substitute a different sampler when one is passed, which would make the
sampling distribution depend on whether the caller seeded.

Where a seed is honoured it fixes the sampled circuit only. A whole board also
depends on the mine-index draw in `span_random_stabilizer_mines` and on
measurement outcomes, both of which use the global NumPy stream, so pinning a
board still means seeding that stream.

The backends also sample from different distributions: Stim and Qiskit draw
uniform Cliffords while chppy draws a scrambling circuit.
`span_random_stabilizer_mines` rejection-samples for the properties the game
needs, so uniformity is not a rule the game depends on, and no interface claims
it.

## Entanglement probes

Entanglement probes are a game rule. A game's probe rules come from one setup
choice, a region count: 0 for none, 1 for area A against the rest, 2 to add
area B and the mutual information between them. Simple Setup applies
`PROBE_REGION_DEFAULT` wherever entanglement can appear — entanglement level 2
and up, whose boards are prepared entangled, and Sandbox, whose two-qubit gates
let the player entangle cells — and 0 elsewhere; Advanced Setup offers every
count the game implements.

The web interface selects an area by clicking single cells, by dragging a
rectangle across the board, or by shift-clicking to extend a rectangle from the
last cell clicked. A drag that starts inside the region being edited erases its
rectangle instead of drawing one. Dragging is a pointer convenience only: every
gesture is also reachable by keyboard, and a region need not be connected or
rectangular. Two selected regions must be disjoint. The complement is always all remaining board qubits, including
revealed cells. Selection never changes the state or gate-target legality.

Editing a region is a frontend selection mode, like the move tools it sits
beside: exactly one of them is armed, and it decides what a cell click does.
Arming a region clears the tool row's highlight, choosing a tool drops the
armed region, and both share the one hint line under the move buttons. The
probe panel is therefore a readout — region sizes and the entropy or mutual
information — and never a second place to look for what a click will do.

`StabilizerQuantumState.entanglement_entropy(subset)` returns the von Neumann
entropy of the selected reduced state in bits. The complete state is pure,
conditioned on recorded measurement outcomes, so this is entanglement entropy
between the subset and its complement. Implementations use binary stabilizer
rank calculations rather than exponentially sized density matrices.

The framework-free `probe_regions` query validates regions and game rules.
It returns S(A) and, when B is supplied, S(B), S(A union B), and mutual
information I(A:B) = S(A) + S(B) - S(A union B). Mutual information measures
total correlations; it must not be labelled as general pairwise entanglement.
For independent Bell pairs, S(A) counts split pairs and I(A:B)/2 counts pairs
connecting A and B. This interpretation does not extend to arbitrary
multipartite states. The existing sum of single-cell entropies remains a
separate observable.

Two separate settings govern the feature, and they answer different questions.
`ENABLE_ENTANGLEMENT_PROBES` is application configuration: a boolean saying
whether this deployment has the diagnostic at all. The region count is a game
tier chosen per game in Setup, bounded by `PROBE_REGION_LIMIT` in `engine.py`,
the count the query implements. Adding a third region is then a change to that
limit and the query, not a new flag.

A deployment with probes switched off contributes a region limit of 0, and the
limit is applied on every game construction, so it hides the setup control,
narrows the rules of each new game including new-same, and can never switch on
a rule the setup did not ask for.

Both web runtimes use the same query and renderer. The server exposes a
read-only POST `/probe`; the browser uses `BrowserSession.probe`. Queries do
not count as moves or consume randomness. Game rule flags travel in app
configuration, separate from serialized state. Area selections are temporary
frontend state, clear on reset/new game/reload, and are not quantum snapshots.
Browser saves preserve the rule flags; version-1 saves without them restore
the defaults (probes on, two-area mode off).

Entropy is evaluated only for an active selection, after edits or completed
moves. The frontend invalidates pending results when selections or game state
change, so an older response cannot replace a newer diagnostic.

## Browser-only distribution

`src/qminesweeper/browser.py` owns an in-memory `BrowserSession`. Setup, move,
reset, and new-same operations all return the shared serialized state.

The browser session can export and import a versioned snapshot containing setup
parameters, game status, preparation circuit, clue and flood-fill settings,
exploration and pin state, measured outcomes, and the chppy tableau. The web
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
`entanglement_score()`, are the main chppy render cost. Optimize only from
measured browser evidence. Preferred mitigations are backend-agnostic
expectation caching, invalidation after measurements and gates, and lazy or
throttled entanglement display before reducing supported board sizes.

## Deliberately deferred features

- Basis-changing clues are an exploratory Sandbox teaching feature. Identify
  and Clear semantics remain Z-basis unless a separate ruleset is designed, and
  the material must say that clue basis changes the diagnostic, not the
  definition of a mine.
- Circuit history, challenges, scoring, and RL tooling should build on the
  shared engine contract and its deterministic seeds rather than introduce
  parallel state models.
- Cross-backend seeded reproducibility is deferred, not pending. Delivering it
  means moving random-Clifford sampling out of `QuantumBackend` into one shared
  seeded sampler, because no per-backend fix can reach it: Stim cannot seed
  `Tableau.random`, and the browser runs chppy under Pyodide, so a Stim-side
  fix would never apply there. Waiting on upstream does not help either —
  quantumlib/Stim#1099 proposes `stim.TableauSampler(k, seed=...)` but is
  unmerged, and warns that a seeded sequence is stable across neither Stim
  versions nor CPU SIMD builds. Revisit only if reproducible shared boards
  become a product requirement, such as challenge seeds or published boards,
  and weigh it against the rule above that the backends stay independent.
