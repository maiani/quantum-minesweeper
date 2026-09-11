# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Browser application and statistics

- Added an installable, offline-capable PWA at `/app/`, built into the Docker
  image and controlled by `QMS_ENABLE_BROWSER_APP`. When enabled it becomes the
  temporary redirect target for `/`; the server-rendered game remains at
  `/setup`. The app routes are exempt from Basic Auth so service-worker updates
  work, while the server game and admin remain protected.
- Added optional browser-game statistics through `POST /analytics`.
  `BrowserSession` records the same fields and counting rules as server games,
  queues reports while offline, and stores them as client-asserted
  `source='browser'` rows that cannot overwrite server-owned games. The ingest
  response also supplies the online-player count shown by reporting clients.
- Hardened the public statistics endpoint with strict shared-vocabulary
  validation, ordered and future-bounded timestamps, per-client and global rate
  limits, retention pruning, and a maximum browser-row count. Rate-limited and
  server-error responses retain the browser queue for retry.
- Added PWA icons, install metadata, a content-fingerprinted service worker,
  network-first application updates, and explicit update checks on visibility
  changes and every hour. Pyodide startup now has staged progress feedback and
  locks setup controls against duplicate starts.

### Configuration and architecture

- Made typed `Settings` the configuration owner: backend and reset policy use
  closed values, and one immutable product snapshot drives the uppercase Jinja
  and lowercase JavaScript projections. CLI backend overrides now survive
  Uvicorn reload.
- Persisted the admin-owned feature snapshot in SQLite. `/app/config` propagates
  probe availability, reset policy, and survey behavior to new PWA games without
  an image rebuild; offline play retains the bundled snapshot.
- Moved both packages to `src/`, split application and standalone-library tests,
  and made the browser bundle serve `qminesweeper` and `chppy` from one module
  manifest. FastAPI context now lives in `server.py`, with shared presentation
  projections in `view_context.py`.
- Replaced the Makefile wrapper with locked Pixi tasks, unified the installed
  and module CLI entrypoints, and aligned TUI parsing, frontend gate arity, and
  the extended two-qubit `CZ` move with shared definitions.

### Entanglement probes

- Added default-on, read-only region probes with cell, rectangle, and
  shift-click selection. Setup chooses zero, one, or two regions; the second
  enables mutual information. Probe rules survive reset, new-same, and browser
  save/restore, while `QMS_ENABLE_ENTANGLEMENT_PROBES` bounds every new game.
- Added independently implemented, non-destructive subset entropy to the chppy,
  Stim, and Qiskit state APIs with parity coverage. The UI and teaching material
  distinguish region entropy and mutual information from the existing sum of
  single-cell entropies.

### Backends

- Extracted the NumPy stabilizer tableau into the independently tested, vendored
  `chppy` package, kept free of application dependencies and terminology.
- **Breaking:** renamed the pure-Python backend from `purepy` to `chppy`.
  `QMS_BACKEND=purepy`, `--backend purepy`, `PurePyBackend`, and `PurePyState`
  are no longer supported; use their chppy equivalents. Deployed servers still
  default to Stim.
- Fixed `StimBackend.random_clifford_circuit` accepting but dropping `seed`, and
  made `ChppyBackend` honor it without disturbing the global NumPy stream. Seeds
  remain best-effort and backend-specific because Stim cannot seed this routine.

### Interface, documentation, and fixes

- Refined the shared UI with grouped mine and entanglement counters, contextual
  help fixes, a shared About overlay, the WINQ and theme-aware Nordita footer
  logos, and README project, status, and play badges.
- Put admin statistics reads and CSV export behind lock-guarded `SQLiteStore`
  methods. Empty databases now render a useful dashboard state and CSV header.
- Fixed CI and deploy lint paths after the `src/` migration, isolated tests from
  developer databases, and included the license in Docker packaging stages.
- Consolidated architecture and active planning into `docs/architecture.md` and
  `docs/roadmap.md`. The companion paper now uses
  `manuscript/qminesweeper.tex` as its single canonical source, with its
  repository connected to the authors' Overleaf project.

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
