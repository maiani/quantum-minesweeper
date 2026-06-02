// static/scripts/engine.js
// =============================================================================
// The "engine" is the seam between the UI and "apply a move, get new state".
//
// In server mode (this file, HttpEngine) a move is a POST to /move that returns
// the new game-state JSON. In the future browser build, a PyodideEngine with the
// SAME move() method will run the game in-page and return the same state shape —
// so the renderer and the rest of the UI don't change between modes.
//
// Contract:  engine.move(gameId, cmd) -> Promise<state>
//   `cmd`   : a move command string (e.g. "2,3", "X 1,1", "CX 1,1 2,2"),
//   resolves to the new game-state dict (same shape as engine.serialize_game),
//   or to an object like { error, redirect } if the game no longer exists.
// =============================================================================

class HttpEngine {
  async move(gameId, cmd) {
    const res = await fetch(`/move?game_id=${encodeURIComponent(gameId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      // The server still reads `cmd` (and game_id) as form fields.
      body: new URLSearchParams({ game_id: gameId, cmd }),
    });
    // Both the success body (state) and the 404 body ({error, redirect}) are JSON.
    return res.json();
  }
}

// The active engine. Phase 2E will replace this with a PyodideEngine in the
// browser-only build; everything else keys off window.GameEngine.
window.GameEngine = new HttpEngine();
