// static/scripts/engine.js
// =============================================================================
// The "engine" is the seam between the UI and "apply a move, get new state".
//
// In server mode (this file, HttpEngine) a move is a POST to /move that returns
// the new game-state JSON. In the browser build, the PyodideEngine in
// pyodide-engine.js has the SAME move() method, runs the game in-page and
// returns the same state shape — so the renderer and the rest of the UI don't
// change between modes.
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

  async probe(gameId, areaA, areaB = null) {
    const res = await fetch(`/probe?game_id=${encodeURIComponent(gameId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area_a: areaA, area_b: areaB }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || result.error || "Probe failed");
    return result;
  }
}

// The active engine. The browser-only build replaces it with a PyodideEngine
// (see browser-main.js); everything else keys off window.GameEngine.
window.GameEngine = new HttpEngine();
