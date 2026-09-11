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

- Fixed board layout so every column of every offered board size is visible and
  clickable at every width. Tile size is now derived from the width the board
  container actually has rather than from the viewport, so wide boards shrink
  their cells to fit instead of being clipped by the page, and small boards on a
  phone grow to fill the screen instead of leaving a third of it empty. A board
  that cannot fit even at the minimum readable tile size now scrolls sideways.
- Fixed the page header overlapping the first row of content between roughly 480
  and 600 pixels wide, where the header wrapped to two lines but the page was
  still offset by a fixed 56 pixels. The header is now sticky and takes its real
  height, the title no longer wraps, and the online-player count gives way on
  narrow screens rather than forcing the row to wrap.
- Reworked the clue colour ramp. It keeps its green-for-low, red-for-high
  reading, but is now drawn per theme, so clues are legible on the light theme
  where the previous ramp fell to roughly 1.7:1 contrast. Contrast against the
  explored cell a clue is actually drawn on is now at least 5.8:1 on the dark
  theme and at least 4.2:1 on the light one, where a green light enough to read
  as green cannot reach the 4.5:1 AA threshold on any light background; clue
  digits are semibold to carry the difference. The ramp also spans the clue
  range boards actually produce instead of the theoretical maximum, so
  neighbouring values such as 1 and 2 are told apart at a glance.
- Made explored and unexplored cells read as different surfaces. Previously
  only a zero clue changed a cell's background, so a revealed clue was drawn on
  exactly the same tile as the unexplored cell beside it. Every explored cell,
  clue and mine included, is now recessed and every unexplored one raised, in
  both themes. The board no longer flattens into the explored colour when the
  game ends.
- Compacted the entanglement probe from a five-block panel to a single row,
  164px down to 42px. The heading duplicated the contextual help the section
  already opens on hover, and the counts line restated the buttons above it, so
  each region's size now rides on its own button and the readout sits at the end
  of the same row. It names its quantity as S(A : rest) or I(A : B), the
  notation the help pane and the paper already use, instead of a sentence. The
  move tools sit 122px higher as a result, back above the fold on a laptop, and
  the row holds to one line down to phone width.
- Fixed the region drag preview and its anchor ring being drawn in the same
  blue whichever region was armed, so editing region B looked identical to
  editing region A. Both now take the armed region's own colour.
- Fixed installed PWAs staying on an old build after a deploy. The bundle was
  served with `etag` and `last-modified` but no `Cache-Control`, and a browser
  with no explicit freshness invents one of roughly a tenth of the file's age,
  so a bundle that had been live a couple of months was treated as fresh for
  days. The service worker is network-first, but its `fetch()` reads through
  that same HTTP cache, which defeated the update path entirely. Both static
  mounts now send `Cache-Control: no-cache` — store, but revalidate — so an
  unchanged file still costs only an empty 304 and offline play is untouched.
- Stopped the setup page inviting players to a survey that was never
  configured: the invitation now needs a URL as well as the feature switch,
  matching the game-over survey button and the header's tutorial link, which
  already required both.
- Replaced the footer's "GitHub" text with the GitHub mark, inlined and painted
  in `currentColor` like the Nordita logo so it follows the footer's link colour
  on both themes.
- Fixed Advanced Setup, where every input and select had collapsed to about
  30px wide and showed only the first character of its value. The entanglement
  probe setting is wrapped in a div so the deployment switch can hide it, and
  that wrapper was a grid item in the form's max-content label column, sized to
  the widest option text inside it; the value column got what was left. Form
  fields also take the full column now rather than four fifths of it, which was
  truncating the longest option mid-word.
- Consolidated the colour system. Every colour literal outside the two theme
  blocks is gone, replaced by new `--on-accent`, `--border`, `--win`,
  `--probe-a`, `--probe-b`, and `--shadow-subtle` tokens, and three properties
  that were referenced but never defined are gone with them: `--white`,
  `--black`, and an undefined `--shadow-subtle`, each of which silently
  invalidated its declaration. Selected tool buttons had therefore been
  inheriting the foreground colour onto their own accent fill at about 1.9:1;
  buttons had no shadow; and hover had no colour change. Fixed with them: the
  loss message now uses the same red each theme draws mines in instead of
  hard-coding the light theme's, the win message has a token rather than a
  fixed green shared by both themes, and the status-counter hover tint and
  admin table no longer paint dark-theme colours onto the light theme. The help
  sidebar's dead `#2d3c58` rule, overridden where it stood, is removed.
- Made the light theme's help sidebar as translucent as the dark theme's. It
  was pinned at 0.95 alpha against the dark theme's 0.55, so the same panel
  read as frosted glass on one theme and a solid wall on the other.
- Rebalanced the light theme, whose page, tile, and explored-cell greys sat
  within about three percent luminance of each other and left the grid
  effectively invisible. The three surfaces are now clearly separated and
  ordered as the dark theme orders them, on a slightly blue ground that lets
  cards, the header, and the board read as distinct layers.
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
