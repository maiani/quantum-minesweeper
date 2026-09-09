# Agent Instructions

Quantum Minesweeper contains a playable game and its companion paper. Before
changing behavior or structure, read [`docs/roadmap.md`](docs/roadmap.md) and
[`docs/architecture.md`](docs/architecture.md). Keep rules, code, user-facing
documentation, and paper terminology aligned.

## Repository map

`src/` holds two importable packages: the game, and the standalone `chppy`
stabilizer library it vendors. Tests mirror that split under `tests/`.

- `src/qminesweeper/game.py`: rules and win conditions.
- `src/qminesweeper/board.py`: board mechanics and exported state.
- `src/qminesweeper/quantum_backend.py`: simulator interface and the single
  source for one- and two-qubit gate arity.
- `src/qminesweeper/{chppy,stim,qiskit}_backend.py`: simulator implementations.
- `src/qminesweeper/engine.py`: framework-free commands, setup validation, game
  construction, and `serialize_game`.
- `src/qminesweeper/browser.py`: Pyodide-safe in-browser session on chppy.
- `src/qminesweeper/server.py`: FastAPI and Jinja server runtime.
- `src/qminesweeper/static/scripts/render.js`: shared game renderer.
- `src/qminesweeper/static/`: shared frontend assets and contextual help.
- `src/qminesweeper/docs/`: user-facing setup and About content rendered in-app.
- `src/chppy/`: vendored standalone stabilizer library; see the rule below
  before touching it.
- `tests/qminesweeper/`, `tests/chppy/`: one suite per package, each with its
  own `conftest.py`.
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
- Import optional simulators lazily. Local and browser runs default to chppy;
  Docker/server deployment defaults to Stim.
- Declare gate arity only in `quantum_backend.py`; do not duplicate the split.
  `src/chppy/` is the one exception, for the reason in its own rule below.
- Keep Cloud Run optional. Browser distribution must remain a first-class mode,
  not a forked product.

The TUI uses the shared engine command parser and dispatcher while retaining its
own setup and lifecycle flow. Check it whenever a shared interface changes.

## `chppy` is an independent project

Treat `src/chppy/` as a separate library that is vendored here, not as part of
this application. It is kept ready to branch out into its own repository if we
decide to, so every change must leave it extractable: copy `src/chppy/` and
`tests/chppy/`, with no edits.

- Develop it as its own project: numpy is its only dependency. Allow no imports
  from this repository, and no references to the rest of the code in comments,
  docstrings, or examples — do not name this game, its modules, its tests, its
  documentation, or its terminology there.
- Define its public surface only in terms of qubits, gate-name strings, and
  Pauli bases. Application meaning belongs in the calling adapter.
- Accept the resulting duplication. It re-declares the gate-arity split and the
  subset validator on purpose; keep those copies in sync by hand rather than
  importing the shared definitions.
- Couple to it in one direction only. `qminesweeper/chppy_backend.py` is the
  sole adapter, and it absorbs any mismatch between game contracts and the
  library.
- Test it on its own terms in `tests/chppy/`, against independently computed
  reference values rather than another simulator, so the suite needs no
  optional dependencies. Keep application fixtures out of any `conftest.py`
  above that directory, and do not add `tests/chppy/__init__.py` — it would
  shadow the package under test.

If a change to it seems to require reaching into the application, the change
belongs in the adapter instead.

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

- Implemented rules and win semantics: `src/qminesweeper/game.py`.
- Board mechanics and exported grid semantics: `src/qminesweeper/board.py`.
- Gate vocabulary and arity: `src/qminesweeper/quantum_backend.py`.
- Commands, setup validation, and serialized state contract:
  `src/qminesweeper/engine.py`.
- Visible game presentation and tool layout: `render.js` and `tools.js`.
- Shared visible page structure: Jinja templates under
  `src/qminesweeper/templates/`.
- Stable design decisions: `docs/architecture.md`.
- Active priorities and deferred work: `docs/roadmap.md`.
- Released behavior: `CHANGELOG.md` and the tagged implementation.

Documentation explains these sources; it must not independently redefine them.
When behavior, terminology, configuration, or a public interface changes, audit
and update the applicable README, user docs, contextual help, architecture,
roadmap, changelog, and manuscript. If code and documentation
conflict, establish the intended behavior first, then update every dependent
description consistently.

- `manuscript/` is a separate git repository, ignored by this one, whose
  `origin` is the authors' Overleaf project. `manuscript/qminesweeper.tex` and
  `manuscript/qminesweeper.bib` are the single canonical source; the earlier
  `_staging` copies were merged into them and no longer exist.
- Propose paper changes as edits to those files, and leave committing and
  pushing to Overleaf to the user. Do not push that repository.
- Keep paper statements mathematically consistent with implemented behavior.
  Mark future work and alternative rules explicitly.
- In particular, keep expectation-value clues, win-condition semantics,
  stabilizer restrictions, region-entropy status, and browser distribution
  synchronized.
