// static/scripts/pyodide-engine.js
// =============================================================================
// Browser-mode engine: runs the pure-Python game inside Pyodide, in the page,
// with NO server. It implements the same contract as HttpEngine
// (engine.js) — `move(gameId, cmd) -> Promise<state>` — so render.js and tools.js
// don't change between server mode and browser mode.
//
// Extra methods used by the browser-entry page: `setup(params)` starts a game,
// `reset()` / `newSame()` handle lifecycle actions, and `exportSave()` /
// `importSave(snapshot)` bridge BrowserSession's versioned save snapshots to
// localStorage.
//
// Requires Pyodide's loader (`loadPyodide`) to be available — the static build
// includes pyodide.js from the CDN before this script. The Python sources are
// fetched from `pyBaseURL` and written into Pyodide's in-memory filesystem.
// =============================================================================

// The set of pure-Python modules to load is NOT hardcoded here. It is the build
// script's job (scripts/build_browser.py) to decide which Stim-free modules ship
// to the browser, and it writes that list into the bundle as `modules.json`
// (next to the .py files). We fetch that manifest at boot so there is a single
// source of truth — adding a pure module to build_browser.py is enough; this
// file never needs editing. Import order doesn't matter (Python resolves deps).
const QMS_PY_MANIFEST = "modules.json";

// Weighted boot stages, used to report progress while `_boot()` runs (the first
// game start has to download ~10 MB of Pyodide, so the UI needs something better
// than a static line of text).
//
//   at    : fraction of the whole boot already done when the stage STARTS
//   until : fraction at which the stage ends, i.e. where the next one starts
//
// Only the module-fetch stage can report true progress (we know how many files
// there are). Pyodide's loader exposes no byte-level download progress, so the
// runtime and numpy stages report just their start; the caller is handed `until`
// as well so it can animate within a stage without ever overshooting it. The
// weights are rough wall-clock shares on a cold cache, not measurements.
const QMS_BOOT_STAGES = {
  runtime: { at: 0.02, until: 0.55, message: "Downloading the Python runtime…" },
  numpy: { at: 0.55, until: 0.72, message: "Loading numpy…" },
  modules: { at: 0.72, until: 0.92, message: "Loading game modules…" },
  session: { at: 0.94, until: 0.99, message: "Starting the game engine…" },
  done: { at: 1, until: 1, message: "Ready" },
};

class PyodideEngine {
  // pyBaseURL: where the qminesweeper/*.py sources are served from.
  // indexURL : optional Pyodide dist location (defaults to the CDN the loader uses).
  // cacheBust: build id appended to module fetches so a PWA cache cannot serve
  // a stale modules.json after the Python module set changes.
  // onProgress: optional boot-progress callback, see `_emit` below. Called only
  // during the one real boot; later calls reuse the memoized promise and stay silent.
  constructor({ pyBaseURL = "/py/qminesweeper/", indexURL = null, cacheBust = null, onProgress = null } = {}) {
    this.pyBaseURL = pyBaseURL;
    this.indexURL = indexURL;
    this.cacheBust = cacheBust;
    this.onProgress = onProgress;
    this._ready = null; // memoized boot promise
    this.session = null; // PyProxy of the Python BrowserSession
  }

  // Report boot progress as {fraction, message, creepTo}:
  //   fraction: how much of the boot is genuinely done (0..1)
  //   creepTo : where the current stage ends — the UI may ease toward this while
  //             waiting, but must not pass it until the next report arrives
  // A throwing callback must never break the boot, hence the try/catch.
  _emit(fraction, message, creepTo) {
    if (!this.onProgress) return;
    try {
      this.onProgress({ fraction, message, creepTo: creepTo === undefined ? fraction : creepTo });
    } catch (err) {
      console.warn("boot progress callback failed", err);
    }
  }

  // Boot Pyodide once: load numpy, copy the Python sources into the FS, import
  // the package, and create a BrowserSession. Safe to call repeatedly.
  async ready() {
    if (!this._ready) this._ready = this._boot();
    return this._ready;
  }

  async _boot() {
    const stages = QMS_BOOT_STAGES;
    this._emit(stages.runtime.at, stages.runtime.message, stages.runtime.until);
    const pyodide = await loadPyodide(this.indexURL ? { indexURL: this.indexURL } : undefined);
    this._emit(stages.numpy.at, stages.numpy.message, stages.numpy.until);
    await pyodide.loadPackage(["numpy"]);
    this._emit(stages.modules.at, stages.modules.message, stages.modules.until);
    pyodide.FS.mkdirTree("/lib/qminesweeper");
    // Read the build-emitted module list, then fetch each module it names.
    const manifestURL = this._moduleURL(QMS_PY_MANIFEST);
    const manifestRes = await fetch(manifestURL);
    if (!manifestRes.ok) {
      throw new Error(`failed to fetch module manifest ${manifestURL}: ${manifestRes.status}`);
    }
    const modules = await manifestRes.json();
    // The only stage with real progress: count modules as each one lands.
    const span = stages.modules.until - stages.modules.at;
    let loaded = 0;
    await Promise.all(
      modules.map(async (name) => {
        const url = this._moduleURL(name);
        const res = await fetch(url);
        if (!res.ok) throw new Error(`failed to fetch ${url}: ${res.status}`);
        pyodide.FS.writeFile("/lib/qminesweeper/" + name, await res.text());
        loaded += 1;
        this._emit(
          stages.modules.at + (span * loaded) / modules.length,
          `${stages.modules.message} (${loaded}/${modules.length})`,
          stages.modules.until
        );
      })
    );
    this._emit(stages.session.at, stages.session.message, stages.session.until);
    pyodide.runPython('import sys; sys.path.insert(0, "/lib")');
    const browser = pyodide.pyimport("qminesweeper.browser");
    this.pyodide = pyodide;
    this.session = browser.BrowserSession();
    this._emit(stages.done.at, stages.done.message);
  }

  _moduleURL(name) {
    const path = this.pyBaseURL + name;
    if (!this.cacheBust) return path;
    return path + (path.includes("?") ? "&" : "?") + "v=" + encodeURIComponent(this.cacheBust);
  }

  // Convert a returned Python dict (PyProxy) into a plain JS object for render.js,
  // then free the proxy so Pyodide's memory doesn't leak.
  _toState(pyDict) {
    const state = pyDict.toJs({ dict_converter: Object.fromEntries });
    if (pyDict.destroy) pyDict.destroy();
    return state;
  }

  _syncConfig() {
    const config = this._toState(this.session.config());
    if (window.GameRenderer) window.GameRenderer.mergeConfig(config);
  }

  // Start a game from string params {rows, cols, mines, ent_level, win, moves};
  // returns the initial state.
  async setup(params) {
    await this.ready();
    const state = this._toState(this.session.setup(
      params.rows, params.cols, params.mines, params.ent_level, params.win, params.moves,
      params.entanglement_probes, params.two_area_probes
    ));
    this._syncConfig();
    return state;
  }

  // Same signature as HttpEngine.move; gameId is ignored (one in-browser game).
  async move(_gameId, cmd) {
    await this.ready();
    return this._toState(this.session.move(cmd));
  }

  async reset(_gameId) {
    await this.ready();
    return this._toState(this.session.reset());
  }

  async newSame(_gameId) {
    await this.ready();
    const state = this._toState(this.session.new_same());
    this._syncConfig();
    return state;
  }

  async exportSave() {
    await this.ready();
    return this._toState(this.session.export_save());
  }

  async importSave(snapshot) {
    await this.ready();
    const proxy = this.pyodide.toPy(snapshot);
    try {
      const state = this._toState(this.session.import_save(proxy));
      this._syncConfig();
      return state;
    } finally {
      if (proxy.destroy) proxy.destroy();
    }
  }


  async probe(_gameId, areaA, areaB = null) {
    await this.ready();
    const pyA = this.pyodide.toPy(areaA);
    const pyB = areaB === null ? null : this.pyodide.toPy(areaB);
    try {
      return this._toState(this.session.probe(pyA, pyB));
    } finally {
      if (pyA.destroy) pyA.destroy();
      if (pyB && pyB.destroy) pyB.destroy();
    }
  }
}

// Exposed for the browser-entry page, which sets
// window.GameEngine = new PyodideEngine(...) instead of the HttpEngine.
window.PyodideEngine = PyodideEngine;
