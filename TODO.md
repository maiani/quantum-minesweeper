# TODO list

## Phase 1 support

- Add gate counter to the future `GameView`.
  - Track only unitary gate applications as the main circuit-depth/defusing-cost metric.
  - Do not count measurements as the primary score, since a completed game ultimately requires measuring the relevant cells.
  - Keep pin toggles outside scoring unless a future mode explicitly makes pins costly.
- Expose gate-target legality in the future `GameView`.
  - Gates cannot target explored cells by rule.
  - The UI should disable or reject explored-cell targets with a clear message.
  - Preserve the rule intent: do not re-hide explored cells after gates, and do not let gates turn revealed safe cells into surprise mines.

## Later game/research features

- Implement basis-changing clues as a Sandbox-only teaching feature.
  - Treat this as an exploratory visualization, not a core win-condition mode.
  - Let learners compare Z-, X-, and Y-basis expectation clues on the same board.
  - Keep Identify and Clear semantics Z-basis unless a separate ruleset is designed later.
  - Label the UI clearly so players understand that changing clue basis changes the diagnostic, not the definition of a mine.
- Extend the entanglement measure
- Implement the RL agent
- Add circuit history and circuit visualization.
  - Show the preparation circuit that creates the field.
  - Show the player circuit applied while trying to defuse or transform the board.
  - Separate the two histories clearly: setup/preparation is part of the puzzle instance, player gates are part of the solution attempt.
  - Record measurements separately from unitary gates, since they are not reversible circuit layers but are essential to the game trace.
  - Consider a compact stabilizer/Clifford circuit view first, with optional export to Qiskit/OpenQASM or Stim text later.
  - Use the same command history needed for browser persistence and parity testing.
- Explore a luck/postselection diagnostic for measurement outcomes.
  - When a cell with mine probability `p` is measured safe, the player has landed in a branch with probability `1 - p`.
  - Track the cumulative probability of the observed measurement branch as a teaching diagnostic.
  - Present it carefully: this is not classical luck from a pre-sampled hidden board, but conditioning on quantum measurement outcomes.
  - Consider fun names such as branch weight, survival branch, postselection score, or luck meter.
  - Use first in Sandbox/tutorial contexts before making it part of scoring.
  - Avoid rewarding reckless measurement too strongly; if used as a game mechanic, balance it against gate count or risk.
- Add region/boundary entanglement probes (later milestone)
  - Let the player select a connected region, drawn boundary, or cut on the board.
  - Report the bipartite entanglement entropy S(A : Abar) between the selected region and its complement.
  - Use it first as a Sandbox/advanced diagnostic, not as a default beginner clue.
  - Treat it as a strategic clue: high entropy means the regions are correlated; low entropy suggests separable subproblems.
  - Add simulator support, e.g. `entanglement_entropy(subset: list[int])`, behind the backend interface.
  - Implement and test the stabilizer-tableau entropy calculation before wiring the UI.
  - Add backend parity tests where supported, and clear fallbacks/errors where not supported.
  - Later consider game modes where region probes have a move cost or limited budget.
  
## UI

- Implement visual for mine counter and entanglement counter
- Implement visual for the gate counter.
  - Emphasize gate count as the cost of the attempted solution, especially in clear/defuse-style modes.
- Add animations for measurement (`M`) and pin (`P`) moves.
  - `M` animation should communicate measurement/collapse and the reveal of a clue or mine.
  - `P` animation should communicate a reversible player annotation, not a quantum operation.
  - Keep animation timing short enough that repeated play remains responsive.
- Include animation source code and assets in the codebase.
  - Store maintainable animation code under the frontend/static tree, not as opaque exported blobs.
  - Keep generated/minified artifacts out unless they are required by the deployed app.
  - Document how to rebuild or edit the animations.
- Write tutorial
- Design circuit visualization UI.
  - Provide tabs or toggles for preparation circuit and player circuit.
  - Keep it compact enough for small screens; start with a collapsed/expandable panel.
  - Link circuit layers back to board cells where possible.
- Design interaction for region entanglement probes
  - Drag-select cells or draw a boundary/cut.
  - Highlight the selected region and its complement clearly.
  - Show the entropy result near the board without obscuring cells.
  - Include help/tutorial examples showing product states, Bell-pair-like states, and clustered entanglement.

## Learning material

- Add documentation and lecture material for learners who want the quantum background.
  - Explain qubits, computational basis, measurement, collapse, expectation values, and Pauli operators.
  - Explain why mines are represented by the Z-basis `|1>` outcome.
  - Introduce the supported Clifford gates through board-level examples.
  - Explain stabilizer states at an accessible level and why the game uses them.
  - Include guided exercises: classical board, `H` superposition, `X` mine flip, `CX` correlations, Bell-pair-like clues, and entanglement diagnostics.
  - Keep the material aligned with in-game help and the companion paper.
