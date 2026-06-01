# TODO list

## Game related
- Fix the pending unexplored cells that appear after a gate move
- Implement the change of basis for the clues
- Extend the entanglement measure
- Implement the RL agent
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
- Write tutorial
- Design interaction for region entanglement probes
  - Drag-select cells or draw a boundary/cut.
  - Highlight the selected region and its complement clearly.
  - Show the entropy result near the board without obscuring cells.
  - Include help/tutorial examples showing product states, Bell-pair-like states, and clustered entanglement.
