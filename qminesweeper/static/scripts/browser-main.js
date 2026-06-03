// static/scripts/browser-main.js
// =============================================================================
// Bootstrap for the BROWSER-ONLY build (dist/index.html). No server: the game
// runs entirely in the page via PyodideEngine. This file:
//   1. creates the Pyodide engine and makes it the active window.GameEngine
//      (so tools.js submits moves to it, exactly like server mode);
//   2. shows the shared setup UI first, or boots Pyodide to restore a saved
//      browser game when one exists;
//   3. wires the setup form and intercepts the Reset/New-Game/New-Setup actions
//      (render.js builds those as a POST to /game, which doesn't exist here).
//   4. persists the current browser game to localStorage after each change.
//
// Loaded only by the static build, AFTER render.js, tools.js, and
// pyodide-engine.js, and after Pyodide's loader script.
// =============================================================================

(function () {
  const PY_BASE = "py/qminesweeper/"; // relative -> works at any hosting base path
  const SAVE_KEY = "qms_browser_save_v1";

  const engine = new PyodideEngine({ pyBaseURL: PY_BASE, cacheBust: window.QMS_BROWSER_BUILD || null });
  const rawMove = engine.move.bind(engine);
  engine.move = async (gameId, cmd) => {
    const state = await rawMove(gameId, cmd);
    await persistCurrentGame();
    return state;
  };
  window.GameEngine = engine; // tools.js's sendCmd reads this

  const loading = document.getElementById("loading");
  const setupPanel = document.getElementById("browser-setup");
  const pageMain = document.querySelector("main");
  const gameSlotIds = ["status-bar", "board-container", "tools-container", "help-mount", "actions-container"];
  const showLoading = (msg) => { if (loading) { loading.textContent = msg; loading.hidden = false; } };
  const hideLoading = () => { if (loading) loading.hidden = true; };
  const setPageMode = (mode) => {
    document.body.classList.toggle("setup-page", mode === "setup");
    document.body.classList.toggle("game-page", mode === "game");
    if (pageMain) {
      pageMain.classList.toggle("setup-page", mode === "setup");
      pageMain.classList.toggle("game-page", mode === "game");
    }
  };
  const setGameSlotsHidden = (hidden) => {
    for (const id of gameSlotIds) {
      const slot = document.getElementById(id);
      if (slot) slot.hidden = hidden;
    }
  };
  const showSetup = ({ keepMessage = false } = {}) => {
    if (!keepMessage) hideLoading();
    setPageMode("setup");
    setGameSlotsHidden(true);
    if (setupPanel) setupPanel.hidden = false;
  };
  const hideSetup = () => {
    if (setupPanel) setupPanel.hidden = true;
    setPageMode("game");
    setGameSlotsHidden(false);
  };

  function resetToolSelection() {
    localStorage.setItem("qms_tool", "M");
  }

  function paramsFromSetupForm(form) {
    const f = new FormData(form);
    return {
      rows: Number(f.get("rows")),
      cols: Number(f.get("cols")),
      mines: Number(f.get("mines")),
      ent_level: Number(f.get("ent_level")),
      win: f.get("win_condition"),
      moves: f.get("move_set"),
    };
  }

  async function persistCurrentGame() {
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(await engine.exportSave()));
    } catch (err) {
      console.warn("could not save browser game", err);
    }
  }

  function clearSavedGame() {
    try {
      localStorage.removeItem(SAVE_KEY);
    } catch (err) {
      console.warn("could not clear browser save", err);
    }
  }

  async function restoreSavedGame() {
    let raw = null;
    try {
      raw = localStorage.getItem(SAVE_KEY);
    } catch (err) {
      console.warn("could not read browser save", err);
    }
    if (!raw) return null;
    try {
      return await engine.importSave(JSON.parse(raw));
    } catch (err) {
      console.warn("discarding invalid browser save", err);
      clearSavedGame();
      return null;
    }
  }

  // Re-apply the active-tool highlight after a (re)render builds the buttons.
  const highlightTool = () => {
    if (window.setTool) setTool(localStorage.getItem("qms_tool") || "M");
  };

  async function startGame(params) {
    showLoading("Starting game…");
    try {
      const state = await engine.setup(params);
      await persistCurrentGame();
      window.GameRenderer.applyState(state);
      highlightTool();
      hideLoading();
      hideSetup();
    } catch (err) {
      console.error("setup failed", err);
      showLoading("Setup failed: " + (err && err.message ? err.message : err));
      showSetup({ keepMessage: true });
    }
  }

  // The action form (Reset / New Game / New Setup) is built by render.js to POST
  // /game. There is no server here, so intercept it and drive the engine instead.
  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.closest("#actions-container")) return;
    event.preventDefault();
    const action = (event.submitter && event.submitter.value) || "";
    try {
      if (action === "reset") {
        const state = await engine.reset();
        await persistCurrentGame();
        window.GameRenderer.applyState(state);
        highlightTool();
      } else if (action === "new_same") {
        localStorage.setItem("qms_tool", "M");
        const state = await engine.newSame();
        await persistCurrentGame();
        window.GameRenderer.applyState(state);
        highlightTool();
      } else if (action === "new_rules") {
        localStorage.setItem("qms_tool", "M");
        clearSavedGame();
        showSetup();
      }
    } catch (err) {
      console.error("action failed", err);
    }
  });

  // Setup form -> start a game with the chosen parameters.
  if (setupPanel) {
    setupPanel.addEventListener("submit", async (event) => {
      event.preventDefault();
      resetToolSelection();
      await startGame(paramsFromSetupForm(event.target));
    });
  }

  // Match the server's first screen as closely as possible: if there is no saved
  // browser game, show setup immediately and defer the Pyodide download until the
  // user starts a game. If a save exists, boot Pyodide and restore it.
  let hasSave = false;
  try {
    hasSave = Boolean(localStorage.getItem(SAVE_KEY));
  } catch (err) {
    console.warn("could not inspect browser save", err);
  }

  if (!hasSave) {
    showSetup();
    return;
  }

  if (setupPanel) setupPanel.hidden = true;
  setGameSlotsHidden(true);
  showLoading("Loading the Python runtime… (first load downloads a few MB)");
  engine
    .ready()
    .then(async () => {
      showLoading("Restoring saved game…");
      const restored = await restoreSavedGame();
      if (restored) {
        window.GameRenderer.applyState(restored);
        highlightTool();
        hideLoading();
        hideSetup();
      } else {
        showSetup();
      }
    })
    .catch((err) => {
      console.error(err);
      showLoading("Failed to load the runtime: " + err);
    });
})();
