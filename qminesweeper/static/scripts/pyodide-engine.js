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

class PyodideEngine {
  // pyBaseURL: where the qminesweeper/*.py sources are served from.
  // indexURL : optional Pyodide dist location (defaults to the CDN the loader uses).
  // cacheBust: build id appended to module fetches so a PWA cache cannot serve
  // a stale modules.json after the Python module set changes.
  constructor({ pyBaseURL = "/py/qminesweeper/", indexURL = null, cacheBust = null } = {}) {
    this.pyBaseURL = pyBaseURL;
    this.indexURL = indexURL;
    this.cacheBust = cacheBust;
    this._ready = null; // memoized boot promise
    this.session = null; // PyProxy of the Python BrowserSession
  }

  // Boot Pyodide once: load numpy, copy the Python sources into the FS, import
  // the package, and create a BrowserSession. Safe to call repeatedly.
  async ready() {
    if (!this._ready) this._ready = this._boot();
    return this._ready;
  }

  async _boot() {
    const pyodide = await loadPyodide(this.indexURL ? { indexURL: this.indexURL } : undefined);
    await pyodide.loadPackage(["numpy"]);
    pyodide.FS.mkdirTree("/lib/qminesweeper");
    // Read the build-emitted module list, then fetch each module it names.
    const manifestURL = this._moduleURL(QMS_PY_MANIFEST);
    const manifestRes = await fetch(manifestURL);
    if (!manifestRes.ok) {
      throw new Error(`failed to fetch module manifest ${manifestURL}: ${manifestRes.status}`);
    }
    const modules = await manifestRes.json();
    await Promise.all(
      modules.map(async (name) => {
        const url = this._moduleURL(name);
        const res = await fetch(url);
        if (!res.ok) throw new Error(`failed to fetch ${url}: ${res.status}`);
        pyodide.FS.writeFile("/lib/qminesweeper/" + name, await res.text());
      })
    );
    pyodide.runPython('import sys; sys.path.insert(0, "/lib")');
    const browser = pyodide.pyimport("qminesweeper.browser");
    this.pyodide = pyodide;
    this.session = browser.BrowserSession();
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

  // Start a game from string params {rows, cols, mines, ent_level, win, moves};
  // returns the initial state.
  async setup(params) {
    await this.ready();
    return this._toState(
      this.session.setup(params.rows, params.cols, params.mines, params.ent_level, params.win, params.moves)
    );
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
    return this._toState(this.session.new_same());
  }

  async exportSave() {
    await this.ready();
    return this._toState(this.session.export_save());
  }

  async importSave(snapshot) {
    await this.ready();
    const proxy = this.pyodide.toPy(snapshot);
    try {
      return this._toState(this.session.import_save(proxy));
    } finally {
      if (proxy.destroy) proxy.destroy();
    }
  }
}

// Exposed for the browser-entry page (Phase 2G), which will set
// window.GameEngine = new PyodideEngine(...) instead of the HttpEngine.
window.PyodideEngine = PyodideEngine;
