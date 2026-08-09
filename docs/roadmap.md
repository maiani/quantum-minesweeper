# Roadmap

_Last updated: 2026-08-09_

This is the active project roadmap. Stable design decisions live in
[`architecture.md`](architecture.md), and shipped changes in
[`../CHANGELOG.md`](../CHANGELOG.md).

## Current baseline

The browser/Pyodide architecture is implemented through a static PWA bundle.
As of this review:

- the release check passes with 563 tests passing and one optional RL test
  skipped because Gymnasium is not installed;
- Python lint and JavaScript syntax checks pass;
- the wheel, source distribution, and 120-file static bundle build cleanly;
- the generated HTML, manifest, service worker, and Python module manifest are
  served successfully over local HTTP;
- local `main` contains two commits after `v0.3.0` that have not been released;
- a real-browser and deployed-environment validation is still outstanding.

These results are a dated development baseline, not a permanent compatibility
guarantee.

## Active priorities

### 1. Validate the browser release candidate

- Run `just browser-serve` in a real desktop and mobile browser.
- Exercise simple and advanced setup, all move types, reset, new game, new
  setup, save/restore, About, Help, and dark/light themes.
- Check Pyodide download and boot messaging, first-game startup, and behavior
  after reload.
- Verify PWA installation, update behavior, and offline startup after the first
  successful load.
- Compare generated pages with server mode for header, footer, setup docs, help
  controls, responsive layout, and accessibility.

### 2. Publish the post-0.3 work

- Review the two local commits after `v0.3.0` and push them to the shared branch.
- Confirm CI across Python 3.11, 3.12, and 3.13, package build, and Docker build.
- Decide whether the changes warrant `v0.3.1` or a larger release.
- Update version metadata and finalize the Unreleased changelog section before
  tagging.

### 3. Refresh deployment confidence

- Smoke-test the FastAPI server with PurePy and Stim.
- Verify Docker startup and Cloud Run configuration without changing deployment
  state during the diagnostic pass.
- Confirm analytics, authentication, admin access, base URLs, and optional links
  with production-like configuration.
- Review pending dependency-update branches and merge only after CI validation.

### 4. Measure browser performance before optimizing

A local Python benchmark on 2026-08-09 measured about 42 ms for PurePy
whole-board observables on the largest 375-qubit preset. This suggests no urgent
desktop-side optimization, but it does not measure Pyodide, rendering, or mobile
hardware.

- Benchmark representative boards inside the browser.
- Profile startup separately from per-move calculation and DOM rendering.
- Add caching or lazy entanglement computation only if measured interaction
  latency warrants it.
- Add a subpath/base-path helper only if actual hosting exposes path failures.

## Near-term product work

### Gameplay and rules

- Add a gate counter as a solution-cost metric.
  - Count unitary gate applications, not measurements.
  - Keep pin toggles outside scoring unless a future mode makes pins costly.
- Make gate-target legality explicit in the UI.
  - Gates cannot target explored cells.
  - Disable or reject illegal targets with a clear explanation.
- Explore a measurement-branch diagnostic.
  - Track the cumulative probability of observed measurement outcomes.
  - Present it as quantum branch conditioning, not hidden-board luck.
  - Start in Sandbox or tutorials before considering scoring.
- Add fixed tutorials, challenge seeds, and move-budget or par scoring.

### Circuit history and visualization

- Separate the preparation circuit from player-applied gates.
- Record measurements separately from reversible gate layers.
- Begin with a compact Clifford/stabilizer history.
- Design a small-screen circuit view that links layers to board cells.
- Consider Stim text, Qiskit, or OpenQASM export only after the internal history
  model is stable.

### Learning material and interaction polish

- Improve the mine, entanglement, and future gate-counter visuals.
- Add short measurement and pin animations that distinguish collapse from a
  reversible annotation.
- Keep animation sources and rebuild instructions in the repository.
- Develop tutorials for qubits, measurement, expectation values, Pauli
  operators, Clifford gates, stabilizer states, and guided boards.
- Keep README, in-game help, user docs, and paper staging synchronized when
  rules or terminology change.

## Research backlog

### Region entanglement probes

- Let the player select a connected region, boundary, or cut.
- Report bipartite entropy $S(A : \bar{A})$.
- Add and parity-test a backend API such as
  `entanglement_entropy(subset: list[int]) -> float`.
- Introduce it first as an advanced Sandbox diagnostic.

### Basis-changing clues

- Let learners compare Z-, X-, and Y-basis expectation clues on one board.
- Keep Identify and Clear win semantics in the Z basis unless a separate
  ruleset is explicitly designed.
- State clearly that clue basis changes the diagnostic, not the definition of a
  mine.

### RL and research tools

- Stabilize command history and deterministic replay before expanding the RL
  environment.
- Reuse deterministic seeds and the shared engine contract for training and
  evaluation.
