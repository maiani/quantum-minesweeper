# Agent Instructions

Quantum Minesweeper contains a playable game and its companion paper. Before
changing behavior or structure, read [`docs/roadmap.md`](docs/roadmap.md) and
[`docs/architecture.md`](docs/architecture.md). Keep rules, code, user-facing
documentation, and paper terminology aligned.

## Repository map

- `qminesweeper/game.py`: rules and win conditions.
- `qminesweeper/board.py`: board mechanics and exported state.
- `qminesweeper/quantum_backend.py`: simulator interface and the single source
  for one- and two-qubit gate arity.
- `qminesweeper/{purepy,stim,qiskit}_backend.py`: simulator implementations.
- `qminesweeper/engine.py`: framework-free commands, setup validation, game
  construction, and `serialize_game`.
- `qminesweeper/browser.py`: Pyodide-safe in-browser session on PurePy.
- `qminesweeper/server.py`: FastAPI and Jinja server runtime.
- `qminesweeper/static/scripts/render.js`: shared game renderer.
- `qminesweeper/static/`: shared frontend assets and contextual help.
- `qminesweeper/docs/`: user-facing setup and About content rendered in-app.
- `scripts/build_browser.py`: static PWA build.
- `manuscript/`: ignored companion-paper workspace; see the paper rules below.

Use Pixi as the development environment and task interface. Run
`pixi task list` to list tasks. Keep
substantive logic in Python or `scripts/`, not in task-runner recipes.

## Rules that must stay true

- Each cell is one qubit; a mine is the Z-basis outcome $|1\rangle$.
- Mine probability is
  $p_i = \langle M_i\rangle = (1 - \langle Z_i\rangle) / 2$.
- A clue is the sum of neighboring Z-basis mine probabilities.
- The supported model is stabilizer/Clifford.
- `Identify`, `Clear`, and `Sandbox` are win conditions; move sets are separate.
- Pinning is a player annotation, not a quantum operation.
- Gates cannot target explored cells. Explored cells are revealed classical
  information and must not be transformed or re-hidden.
- The status bar's entanglement score is the sum of local single-qubit
  entropies. Region bipartite entropy S(A : rest) and mutual information
  I(A:B) are the separate read-only entanglement probe; keep the two
  observables distinct in code, documentation, and the paper.

Do not silently change these semantics. If exploring a variant, label it as
such in code, documentation, and the paper.

## Architecture guardrails

- Maintain one product across server and browser runtimes. Share rules,
  serializer, renderer, templates, documentation, and terminology.
- Keep `engine.py` framework-free and Pyodide-safe: no FastAPI or settings
  imports.
- Use the lean `serialize_game` dictionary and small `Command` set. Do not
  reintroduce parallel `GameView` or `CellView` models.
- Keep game-state payloads presentation-free. Symbols, labels, colours, and
  visible tools belong in JavaScript; feature flags belong in the separate app
  configuration.
- Keep `render.js` as the only game renderer. Replace moved Jinja rendering;
  never retain a second frontend path.
- Treat shared server templates as the visible-page source. Static pages are
  rendered from them at build time with minimal browser-only hooks.
- Evolve existing server routes; do not add a parallel `/api/*` game-state
  namespace.
- Treat `QuantumBackend` as a simulator abstraction, not a deployment runtime.
- Import optional simulators lazily. Local and browser runs default to PurePy;
  Docker/server deployment defaults to Stim.
- Declare gate arity only in `quantum_backend.py`; do not duplicate the split.
- Keep Cloud Run optional. Browser distribution must remain a first-class mode,
  not a forked product.

The TUI uses the shared engine command parser and dispatcher while retaining its
own setup and lifecycle flow. Check it whenever a shared interface changes.

## Implementation and verification

- Use deterministic seeds in tests that pin board state or backend parity.
- Add or update tests for rule changes, gate behavior, serialization, command
  parsing, setup validation, and browser save/restore.
- Run `pixi run check` for Ruff, pytest, and JavaScript syntax checks.
- Run `pixi run release-check` when changing packaging, static assets, templates,
  browser modules, or release behavior.
- Run `pixi run icons` only when the SVG icon source changes; ordinary browser
  builds use the tracked PNG files.
- Test all applicable simulator backends. Do not claim optional-backend parity
  from a default-only run.
- There is no repository JS test framework. For renderer changes, add a
  throwaway jsdom/Node check and perform a live server/browser smoke test.
- Comment non-obvious JavaScript generously; the maintainer is less familiar
  with JS. Keep Python interfaces and numerical conventions documented too.
- Preserve unrelated and generated work. Do not make opportunistic cleanup part
  of a scoped change.

## Current work

[`docs/roadmap.md`](docs/roadmap.md) is the only current-work list and the
authority on task status and priority. Do not restate its tasks here, in
`architecture.md`, or in any second checklist.

Each file owns one kind of statement:

- This file: standing rules and per-change practice.
- [`docs/architecture.md`](docs/architecture.md): stable decisions and
  deliberate constraints, including features deferred on purpose.
- [`docs/roadmap.md`](docs/roadmap.md): work still to be done.
- [`CHANGELOG.md`](CHANGELOG.md): what shipped.

Follow the roadmap's own maintenance rule: update it in the same change that
completes, removes, reprioritizes, or materially redefines an item.

## Documentation and paper

Keep documentation synchronized with the implementation in the same scoped
change. Do not leave conflicting descriptions for a later cleanup.

Use this source-of-truth hierarchy:

- Implemented rules and win semantics: `qminesweeper/game.py`.
- Board mechanics and exported grid semantics: `qminesweeper/board.py`.
- Gate vocabulary and arity: `qminesweeper/quantum_backend.py`.
- Commands, setup validation, and serialized state contract:
  `qminesweeper/engine.py`.
- Visible game presentation and tool layout: `render.js` and `tools.js`.
- Shared visible page structure: Jinja templates under
  `qminesweeper/templates/`.
- Stable design decisions: `docs/architecture.md`.
- Active priorities and deferred work: `docs/roadmap.md`.
- Released behavior: `CHANGELOG.md` and the tagged implementation.

Documentation explains these sources; it must not independently redefine them.
When behavior, terminology, configuration, or a public interface changes, audit
and update the applicable README, user docs, contextual help, architecture,
roadmap, changelog, and manuscript staging copy. If code and documentation
conflict, establish the intended behavior first, then update every dependent
description consistently.

- `manuscript/qminesweeper.tex` and `manuscript/qminesweeper.bib` are canonical
  files owned by the authors. Do not edit them.
- Propose paper changes only in `manuscript/qminesweeper_staging.tex` and
  `manuscript/qminesweeper_staging.bib`.
- The user incorporates accepted staging changes into the canonical files.
- Keep paper statements mathematically consistent with implemented behavior.
  Mark future work and alternative rules explicitly.
- In particular, keep expectation-value clues, win-condition semantics,
  stabilizer restrictions, region-entropy status, and browser distribution
  synchronized.
