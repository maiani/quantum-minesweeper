# Changelog

All notable changes to this project will be documented in this file.

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
