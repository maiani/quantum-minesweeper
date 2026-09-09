# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Merged the companion paper's staging copy into the canonical
  `manuscript/qminesweeper.tex`, which now supersedes it, and pointed the
  manuscript repository at the authors' Overleaf project. `AGENTS.md` records
  the single-source rule that replaces the staging workflow.
- Fixed `StimBackend.random_clifford_circuit` dropping the `seed` keyword its
  `QuantumBackend` base class declares, which raised `TypeError` on any caller
  that passed one, and added a conformance test covering every backend.
- Made `ChppyBackend.random_clifford_circuit` honour `seed`, giving in-backend
  reproducibility without disturbing the global NumPy stream that unseeded calls
  and the golden export tests use. Stim still cannot seed, so `seed` remains
  best-effort and per-backend, and cross-backend seeded reproducibility is now
  recorded as deliberately deferred in `architecture.md`.
- Extracted the stabilizer tableau into `chppy`, an independent vendored package
  under `src/chppy/`, kept ready to branch out into its own repository. It has no
  references to the rest of the code and its own test suite in `tests/chppy/`,
  checked against independently computed reference values.
- **Breaking:** renamed the pure-Python backend from `purepy` to `chppy`, after
  the library it adapts. `QMS_BACKEND=purepy` and `--backend purepy` are no
  longer accepted and now raise an unknown-backend error; use `chppy`.
  `PurePyBackend`/`PurePyState` became `ChppyBackend`/`ChppyState`. Deployments
  are unaffected: `scripts/deploy.sh` defaults to `stim`.
- Moved the packages under `src/` and split tests to match, as
  `tests/qminesweeper/` and `tests/chppy/`. The game's pytest fixtures moved to
  `tests/qminesweeper/conftest.py` so the chppy suite no longer imports the
  application, and the browser bundle now serves both packages from `dist/py/`
  with its module manifest at that root.
- Added default-on web entanglement probes with cell, drag-rectangle, and
  shift-click selection, and an optional two-area mutual-information comparison
  in Advanced Setup. Region editing is one exclusive selection mode alongside
  the move tools and shares their hint line, leaving the probe panel as a
  readout. Probe rules are preserved by reset, new-same, and browser
  save/restore.
- Added `QMS_ENABLE_ENTANGLEMENT_PROBES`, a deployment switch for the
  entanglement probe, also on the admin dashboard. It bounds every game built,
  including new-same.
- Made the number of probe regions a single per-game setup choice (0, 1, or 2)
  instead of two independent flags. Simple Setup enables probes wherever
  entanglement can appear, at Level 2 and above and in Sandbox; Advanced Setup
  sets any count.
- Added non-destructive subset entropy to the PurePy, Stim, and Qiskit state
  APIs, with independent implementations and backend parity coverage.
- Distinguished the single-cell entropy sum from region entropy and mutual
  information in the interface and teaching material.
- Replaced the status bar's text labels with a mine emoji and an
  interlocked-rings icon, keeping the expectation brackets on ⟨💣⟩, grouped the
  two counters above the board instead of at the page edges (where the help
  sidebar covered the right-hand one), and moved their names and the bit unit
  into the help pane and tooltips.
- Moved admin analytics reads and CSV export behind public, lock-guarded
  `SQLiteStore` methods, so routes no longer reach into the private database
  connection and concurrent reads cannot observe a torn counter snapshot.
- Fixed the contextual help panel swapping back to the activated topic as soon
  as the pointer moved into it, which made a hovered topic unreadable past its
  first screenful. Arming a mode, including a probe region, now also sets the
  topic that hovering returns to.
- Fixed the analytics CSV export to emit column headers when no games exist.
- Replaced the browser build's plain loading text with a staged progress bar for
  the Pyodide boot, and locked the setup form while a game starts.
- Added the WINQ funder logo to the shared footer.
- Replaced the raster Nordita footer logo with an inlined single-colour SVG that
  follows the active theme.
- Added a project logo and status badges to the README.
- Added PWA icons, install metadata, and a content-fingerprinted service worker
  to the static browser build.
- Added optional analytics configuration to generated browser pages.
- Refactored FastAPI application context into `qminesweeper/server.py` and the
  shared `view_context.py` module.
- Added a shared About overlay for server and browser-only modes.
- Moved project architecture and planning documentation to
  `docs/architecture.md` and `docs/roadmap.md` and refreshed their status.
- Replaced the Makefile command wrapper with a locked Pixi development
  environment and native tasks.
- Fixed the installed `qminesweeper` command to use the same package-owned
  Typer application as `python -m qminesweeper`.
- Unified TUI command parsing and move prompts with the shared engine rules,
  synchronized frontend gate arity, and kept `CZ` in the extended two-qubit
  move set.

## [0.3.0] - 2026-06-02
- Added a static browser-only build that runs Quantum Minesweeper in Pyodide on the PurePy backend.
- Added `BrowserSession`, `PyodideEngine`, and browser game persistence through versioned `localStorage` snapshots.
- Shared setup/about/base templates between server and browser builds so the visible pages stay aligned.
- Centralized framework-free setup validation and game construction for server and browser sessions.
- Made PurePy the local/default backend while Docker/server deployments install and default to Stim.
- Moved Stim to an optional dependency extra for local installs.
- Added browser-session tests and Makefile targets for building and serving the static browser bundle.

## [0.2.2] - 2026-06-01
- Hardened the codebase ahead of the browser-backend refactor.
- Fixed dagger-gate command normalization so `Sdg`, `SXdg`, and `SYdg` moves work from the web UI.
- Fixed Stim/Qiskit parity for `SY` and `SYdg`, and added per-gate backend parity tests.
- Fixed Stim single-qubit multi-target gate application and made random Clifford decomposition fail loudly on unknown gates.
- Restored reset-button rendering and aligned sandbox reset policy with the win condition.
- Added setup validation and coordinate bounds checks to avoid invalid boards and wrapped negative indexes.
- Moved admin authentication off URL query parameters and onto a signed session cookie.
- Pinned dependency version ranges and fixed deployment/admin environment variables.
- Added regression coverage for command parsing, flood fill, backend parity, golden grid exports, setup validation, and admin sessions.
- Updated installation and launch instructions.

## [0.2.1] - 2025-09-30 - First public pre-release
- Updated about page
- Updated pre-commit
- FIX: animations not working
- FIX: url color

## [0.2.0] - 2025-09-25
- Polishing of UI and UX
  
## [0.1.4] - 2025-09-25
- Implementing all the animations
- Including survey

## [0.1.3] - 2025-09-25
- Add analytics database
- Add initial support for admin page
- Make possible to change setting at runtime 

## [0.1.2] - 2025-09-23
- Added keyboard input in the webUI
- Add simplified setup
- Add support for documentation
- Add support for online help
- Better configuration handling
- Better logging
- Fixed responsive layout
- Fixed light theme
- Changed bombs -> mines everywhere
- Improved testing
- Remove dependence on qiskit for the bomb spanning
- Added pre-commit
- Align TUI
- Simplify the game.py enums using strings and support two-qubit extended moveset.
- Open graph support
  
## [0.1.1] - 2025-09-15
- Rework authorization module 
- Add single-qubit entropy
  
## [0.1.0] - 2025-09-15
- First private release
