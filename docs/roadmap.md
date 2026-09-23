# Roadmap

_Last updated: 2026-09-11_

This is the source of truth for active work and task status, and the only
current-work list in the repository.

It holds work still to be done, and nothing else. Stable decisions and
deliberate constraints, including features deferred on purpose, live in
[`architecture.md`](architecture.md); shipped changes live in
[`../CHANGELOG.md`](../CHANGELOG.md). A statement that can never be checked off
belongs in one of those files, not here.

Tasks are ordered first by priority and then by category:

- **P0 — Release blockers:** evidence required before the next release.
- **P1 — Architectural correctness:** structural risks to address before broad
  feature expansion or server scaling.
- **P2 — Product and maintainability:** planned gameplay, UX, packaging, and
  documentation improvements.
- **P3 — Research and exploration:** experimental features without a committed
  release target.

Treat each checkbox as a separate, reviewable task. Update this file in the same
change that completes, removes, reprioritizes, or materially redefines an item.

## P0 — Release blockers

None open.

## P1 — Architectural correctness

### Core state ownership

- [ ] Consolidate board/game ownership so commands and serialization cannot
  receive mismatched board and game objects.
- [ ] Decide whether a small framework-free runtime session model is warranted.
- [ ] Keep browser, server, TUI, and RL callers aligned with the resulting
  ownership boundary.

### Browser persistence

- [ ] Replace direct access to private board fields and chppy tableau arrays
  with public, versioned snapshot methods.
- [ ] Validate snapshot shapes, enum values, dimensions, and tableau consistency
  before mutating a live session.
- [ ] Define migration or explicit rejection behavior before changing the save
  schema version.

### Server game store

- [ ] Replace the process-global dictionary of untyped records with an explicit
  game-store/session boundary, following the core ownership decision above.
- [ ] Centralize create, lookup, reset, new-same, heartbeat, outcome, and pruning
  behavior in that boundary.
- [ ] Document whether server games are deliberately ephemeral and
  single-process, or make restart and multi-instance persistence reliable.

### Request concurrency

- [ ] Choose an explicit FastAPI execution model for CPU-bound simulator work
  and synchronous SQLite access.
- [ ] Add per-game locking before allowing threaded or genuinely concurrent
  mutation.
- [ ] Align Cloud Run concurrency, Uvicorn worker assumptions, and documented
  server guarantees with the chosen model.

### Frontend correctness and help

- [x] Derive TUI command tokens and frontend gate arity from the shared move
  definitions in `game.ALLOWED_MOVES` and `quantum_backend`.
- [ ] Replace the hand-maintained `TOOL_ROWS` move-set table in `render.js` with
  the shared per-move-set tokens, so the browser stops restating
  `ALLOWED_MOVES`.
- [ ] Make illegal gate targets visibly unavailable or explain rejection
  clearly.
- [ ] Generate gate visual markup from one template or data source.
- [ ] Remove obsolete inline scripts, absolute-path assumptions, copied markup,
  and the malformed Hadamard visual.
- [ ] Validate every help topic and SVG state during the static build.

## P2 — Product and maintainability

### Browser performance

A local Python benchmark on 2026-08-09 measured about 42 ms for chppy
whole-board observables on the largest 375-qubit preset. This does not measure
Pyodide, DOM rendering, startup, or mobile hardware.

- [ ] Benchmark representative boards inside Pyodide on desktop and mobile.
- [ ] Profile runtime startup, simulator work, observable calculation, and DOM
  rendering separately.
- [ ] Add expectation caching or lazy/throttled entanglement computation only
  if measured interaction latency warrants it; the preferred mitigations are
  recorded under "Performance boundary" in `architecture.md`.

### Packaging boundaries

- [ ] Reassess core, server, browser-build, and research optional dependencies
  now that the CLI entrypoint boundary is stable.
- [ ] Split extras only if the smaller installation is worth the additional
  support matrix.

### Developer workflow and tests

- [ ] Define shared backend parametrization instead of repeating backend class
  lists across tests.
- [ ] Use one JavaScript file-discovery source for pytest and the Pixi
  `js-check` task.
- [ ] Add installed-wheel CLI smoke coverage to the release workflow.

### Scoring and challenges

- [ ] Add a gate counter that counts unitary applications, not measurements or
  pins.
- [ ] Add fixed tutorials, challenge seeds, and move-budget or par scoring.
- [ ] Explore a measurement-branch diagnostic based on cumulative observed
  outcome probability; present it as branch conditioning, not hidden-board
  luck.

### Circuit history and visualization

- [ ] Separate preparation history from player-applied gates.
- [ ] Record measurements separately from reversible gate layers.
- [ ] Design a compact Clifford/stabilizer view that works on small screens and
  links operations to board cells.
- [ ] Consider Stim text, Qiskit, or OpenQASM export only after the internal
  history model is stable.

### Interaction polish

- [ ] Decide the two open light-theme contrast questions recorded under
  "Verification" in `DESIGN.md`: white on `accent-light` is 4.23:1, which
  misses AA for the selected tool button's normal-size text, and the pin glyph
  is 2.58:1 on an unexplored tile.
- [ ] Improve mine and entanglement visuals, and extend them to the gate
  counter once it exists (see "Scoring and challenges").
- [ ] Add short measurement and pin animations that distinguish quantum
  collapse from a reversible player annotation.
- [ ] Keep animation sources and rebuild instructions in the repository.

### Documentation and learning material

- [ ] Develop tutorials for qubits, measurement, expectation values, Pauli
  operators, Clifford gates, stabilizer states, and guided boards.
- [ ] Publish archive and citation guidance when archive metadata is available.

## P3 — Research and exploration

### Live Bloch sphere in contextual help

The `blochkit` renderer is vendored at
`src/qminesweeper/static/scripts/blochkit.js` and adapted in `bloch-help.js`.
`JS_BLOCH_SPHERE` chooses it over the tracked LaTeX-rendered SVGs, which stay
the default and are untouched. Checked by `pixi run bloch-check`.

- [ ] Decide between the live sphere and the tracked SVGs for the ten one-qubit
  gates, then retire whichever loses and remove the flag.
- [ ] Decide whether Measure keeps its collapse animation, which is its first
  illustration rather than a replacement for one.
- [ ] Give the two-qubit gates an illustration: a Bloch sphere draws one qubit,
  so CX/CY/CZ/SWAP keep circuit diagrams and no renderer choice reaches them.
- [ ] Confirm the sphere's palette in use. `axis-x/y/z` are new low-chroma
  tokens, and the rotation axis is `pin`; check both themes on a real screen.
- [ ] Decide whether `blochkit.js` stays vendored in both this repo and
  qapture-the-flag or becomes one shared upstream. Local changes (the named
  gate/ket vocabulary, `MEASURE`, and the shared camera drag) are not yet in
  the other copy.

### Retro theme

A third theme, `html.retro` in `static/styles/base.css`, colour- and
shape-sampled from a reference poster and from the original Windows
Minesweeper's own bevelled chrome and LCD counters. A kept theme, not a
trial. Switched via the same `#toggle-theme` button as dark/light; its three
webfonts (Racing Sans One for the title, VT323 for body text and controls,
Press Start 2P for buttons) load on demand so dark and light stay
offline-complete. See DESIGN.md's Colors, Typography, Elevation & Depth, and
Shapes sections.

- [x] Run the light theme's own per-step clue-ramp contrast audit against
  `--zero-bg` instead of reusing the light theme's numbers as a first pass --
  done; see DESIGN.md's clue-ramp note.
- [ ] Check the bevel treatment (buttons, cards, tiles) on a real narrow-phone
  screen and under `prefers-reduced-motion`/`prefers-contrast`.

### Basis-changing clues

- [ ] Let learners compare Z-, X-, and Y-basis expectation clues.
