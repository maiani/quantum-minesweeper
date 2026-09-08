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

  const engine = new PyodideEngine({
    pyBaseURL: PY_BASE,
    cacheBust: window.QMS_BROWSER_BUILD || null,
    // Hoisted function declaration defined below; it only ever runs while a game
    // is starting, long after this module has finished evaluating.
    onProgress: onBootProgress,
  });
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
  const gameSlotIds = ["status-bar", "board-container", "probe-container", "tools-container", "help-mount", "actions-container"];

  // ---------------------------------------------------------------------------
  // Boot progress bar
  //
  // Starting the first game downloads Pyodide (~10 MB) plus numpy plus the game's
  // own Python modules, which takes seconds on a fast desktop and much longer on a
  // phone. PyodideEngine reports weighted boot stages through `onProgress`; each
  // report carries the fraction genuinely reached and `creepTo`, the fraction where
  // that stage ends.
  //
  // Only the module-fetch stage knows real counts — Pyodide's loader gives us no
  // byte-level download progress — so inside a stage we ease the bar toward
  // `creepTo` on a timer, by a shrinking share of the remaining gap. The bar keeps
  // moving during a long download and never reaches the ceiling on its own, so it
  // can't claim to be finished before the runtime actually is; only a real stage
  // report moves it past that ceiling.
  // ---------------------------------------------------------------------------
  const loadingMessage = document.getElementById("loading-message");
  const loadingTrack = document.getElementById("loading-track");
  const loadingBar = document.getElementById("loading-bar");
  const loadingHint = document.getElementById("loading-hint");

  const CREEP_INTERVAL_MS = 200; // how often the bar eases forward while waiting
  const CREEP_STEP = 0.08; // share of the remaining gap consumed per tick

  let barValue = 0; // fraction currently painted (0..1)
  let barCeiling = 0; // fraction the creep may approach but not reach
  let creepTimer = null;

  const paintBar = () => {
    if (loadingBar) loadingBar.style.width = (barValue * 100).toFixed(1) + "%";
    if (loadingTrack) loadingTrack.setAttribute("aria-valuenow", String(Math.round(barValue * 100)));
  };

  const stopCreep = () => {
    if (creepTimer !== null) {
      clearInterval(creepTimer);
      creepTimer = null;
    }
  };

  const startCreep = () => {
    if (creepTimer !== null) return;
    creepTimer = setInterval(() => {
      // Close enough to the ceiling that further steps are invisible: idle until
      // the next stage report raises it.
      if (barCeiling - barValue < 0.002) {
        stopCreep();
        return;
      }
      barValue += (barCeiling - barValue) * CREEP_STEP;
      paintBar();
    }, CREEP_INTERVAL_MS);
  };

  // Advance (never rewind) the bar. Monotonic so a cheap stage following an
  // expensive one can't look like a regression.
  const showProgress = ({ fraction, creepTo }) => {
    if (!loadingTrack) return;
    loadingTrack.hidden = false;
    if (loadingHint) loadingHint.hidden = false;
    barValue = Math.max(barValue, fraction);
    barCeiling = Math.max(barValue, creepTo);
    paintBar();
    if (barValue >= 1) stopCreep();
    else startCreep();
  };

  const hideProgress = () => {
    stopCreep();
    barValue = 0;
    barCeiling = 0;
    paintBar();
    if (loadingTrack) loadingTrack.hidden = true;
    if (loadingHint) loadingHint.hidden = true;
  };

  const showLoading = (msg) => {
    if (!loading) return;
    if (loadingMessage) loadingMessage.textContent = msg;
    loading.hidden = false;
  };
  // Failures keep the text but drop the bar: a half-filled bar under an error
  // message reads as "still working".
  const showLoadingError = (msg) => {
    hideProgress();
    showLoading(msg);
  };
  const hideLoading = () => {
    hideProgress();
    if (loading) loading.hidden = true;
  };

  function onBootProgress(report) {
    if (report.message) showLoading(report.message);
    showProgress(report);
  }
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
      // Setup chooses a region count (0 none, 1 area A, 2 also area B); the
      // session keeps the two rule flags that count stands for.
      entanglement_probes: Number(f.get("entanglement_probe_regions")) >= 1,
      two_area_probes: Number(f.get("entanglement_probe_regions")) >= 2,
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

  // Lock the setup forms while a game is starting. The first boot takes seconds,
  // and a still-live Start button invites a second submit on top of the one in
  // flight; the panel stays visible so the page doesn't empty out while waiting.
  const setSetupBusy = (busy) => {
    if (!setupPanel) return;
    setupPanel.setAttribute("aria-busy", busy ? "true" : "false");
    for (const btn of setupPanel.querySelectorAll("button")) btn.disabled = busy;
  };

  async function startGame(params) {
    setSetupBusy(true);
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
      showLoadingError("Setup failed: " + (err && err.message ? err.message : err));
      showSetup({ keepMessage: true });
    } finally {
      setSetupBusy(false);
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
        window.GameRenderer.clearProbes();
        const state = await engine.reset();
        await persistCurrentGame();
        window.GameRenderer.applyState(state);
        highlightTool();
      } else if (action === "new_same") {
        window.GameRenderer.clearProbes();
        localStorage.setItem("qms_tool", "M");
        const state = await engine.newSame();
        await persistCurrentGame();
        window.GameRenderer.applyState(state);
        highlightTool();
      } else if (action === "new_rules") {
        window.GameRenderer.clearProbes();
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
  // The engine's own stage reports take over the message as soon as the boot
  // starts; this is only what the user sees for the first few milliseconds.
  showLoading("Loading the Python runtime…");
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
      showLoadingError("Failed to load the runtime: " + err);
    });
})();
