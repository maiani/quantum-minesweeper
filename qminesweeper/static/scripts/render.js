// static/scripts/render.js
// =============================================================================
// Client-side renderer for the game screen.
//
// BIG PICTURE
// -----------
// The server no longer renders the board. Instead `game.html` is a static shell
// containing two JSON blobs and a few empty <div> "slots":
//
//     <script id="game-state" type="application/json"> ...game state... </script>
//     <script id="app-config" type="application/json"> ...feature flags... </script>
//     <div id="status-bar"></div>
//     <div id="board-container"></div>
//     <div id="tools-container"></div>
//     <div id="actions-container"></div>
//
// This file reads those two JSON blobs and *builds* the HTML for each slot in
// JavaScript. So the split of responsibility is:
//   - backend  -> computes GAME STATE (the grid numbers, status, observables);
//   - this file -> turns state into what you SEE (symbols, colours, buttons).
//
// "state" is game data only (see engine.serialize_game in Python). "config" is
// server/build settings (e.g. whether the reset button is allowed). They are
// kept separate on purpose: in the future browser build, the in-browser engine
// produces `state`, while `config` comes from the build.
//
// MOVES: clicking a cell calls the engine (engine.js), which POSTs /move and
// returns the new state; applyState() re-renders in place — no page reload.
// (The reset / new-game / new-setup actions are still plain form POSTs that
// reload the page; those are rare and change the game/URL anyway.)
//
// `clickCell` and `setTool` used below are defined in tools.js. They are only
// *called* later when the user clicks, by which time tools.js has loaded — so it
// is fine to reference them here.
// =============================================================================

// --- Module state -----------------------------------------------------------
// `config` (feature flags) is read once on load and never changes. `gameId` is
// the current game's id, updated on every applyState. `toolsSig` lets us skip
// rebuilding the tool buttons when they wouldn't change (see renderTools).
let _config = {};
let _gameId = null;
let _toolsSig = null;
let _state = null;
let _probeA = new Set();
let _probeB = new Set();
let _probeEdit = null;
let _probeAnchor = null;
let _drag = null;
let _previewCells = new Set();
let _suppressClick = false;
let _probeRequest = 0;
let _probeResult = null;
let _probeError = null;
let _mutationPending = false;

// Read and parse a <script type="application/json"> blob by its id.
// Returns the parsed object, or null if the element is missing / not valid JSON.
function readJson(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  try {
    return JSON.parse(el.textContent); // textContent = the raw JSON text inside the tag
  } catch {
    return null;
  }
}

// Tiny helper to create a DOM element in one call, e.g.
//   el("button", { class: "btn", text: "Hi", onclick: fn }, [childNode])
// - `tag`      : the HTML tag name ("div", "button", ...).
// - `props`    : an object of attributes. Special keys:
//                  class   -> sets the CSS class,
//                  text    -> sets the visible text,
//                  onclick -> attaches a click handler;
//                any other key becomes a plain HTML attribute (e.g. href, value).
// - `children` : a child node (or array of nodes/strings) to nest inside.
function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined) continue; // skip unset props
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "onclick") node.addEventListener("click", value);
    else node.setAttribute(key, value);
  }
  // [].concat(children) lets callers pass either one child or an array of them.
  for (const child of [].concat(children)) {
    if (child == null) continue;
    // A string becomes a text node; anything else is assumed to be a DOM node.
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

// Decode one grid value into how the cell should look.
// The server's grid uses sentinel numbers (see board.export_numeric_grid):
//   -1 = unexplored, -2 = pinned, 9 = definite mine, 0 = empty (clue 0),
//   anything else (0..8, possibly fractional) = a clue value.
// Returns { text, cls, color }: the glyph to show, the CSS class, and (for clues)
// a red→green colour string. This is the ONLY place sentinels are interpreted.
function decodeCell(val) {
  if (val === -1) return { text: "■", cls: "unexplored", color: null };
  if (val === -2) return { text: "⚑", cls: "pinned", color: null };
  if (val === 9) return { text: "💥", cls: "mine", color: null };
  if (val === 0) return { text: " ", cls: "empty", color: null }; // non-breaking space keeps the cell sized
  // Clue: map the value (0..8) onto a red(high)→green(low) gradient.
  const t = Math.max(0.0, Math.min(val / 8.0, 1.0)); // clamp to [0, 1]
  const color = `rgb(${Math.round(255 * t)},${Math.round(255 * (1.0 - t))},0)`;
  return { text: val.toFixed(1), cls: "clue", color }; // one decimal place, e.g. "2.5"
}

// Human-readable labels for screen readers. The board is visually dense, so
// each button names its row/column and the current visible cell state.
function cellAriaLabel(r, c, val, decoded) {
  const prefix = `Row ${r + 1}, column ${c + 1}`;
  if (decoded.cls === "unexplored") return `${prefix}: unexplored cell`;
  if (decoded.cls === "pinned") return `${prefix}: pinned cell`;
  if (decoded.cls === "mine") return `${prefix}: mine outcome`;
  if (decoded.cls === "empty") return `${prefix}: revealed safe cell`;
  return `${prefix}: clue ${val.toFixed(1)}`;
}

// Build an SVG element. `el` cannot: document.createElement would make an
// unknown *HTML* element of the same name, which renders nothing.
const SVG_NS = "http://www.w3.org/2000/svg";
function svg(tag, props = {}, children = []) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(props)) node.setAttribute(key, value);
  for (const child of [].concat(children)) node.appendChild(child);
  return node;
}

// Two interlocked rings: the entanglement counter's icon. Drawn in currentColor
// so it follows the light/dark theme like the text beside it, and sized in `em`
// so it tracks the surrounding font size. There is no emoji for entanglement,
// and a link glyph would suggest pairwise links this number does not measure.
function entanglementIcon() {
  const ring = (cx) => svg("circle", {
    cx, cy: 12, r: 6, fill: "none", stroke: "currentColor", "stroke-width": 2,
  });
  return svg("svg", {
    class: "status-glyph", viewBox: "0 0 24 24", width: "1.15em", height: "1.15em",
    "aria-hidden": "true", focusable: "false",
  }, [ring(8), ring(16)]);
}

// --- Status bar: expected mines on the left, entanglement on the right.
// Each counter is an icon and a number. The icons replace the words in the old
// "⟨Mines⟩ =" and "Local entropy sum =" labels, but the mine counter keeps its
// expectation brackets: ⟨💣⟩ is the expectation value of the mine number, not a
// count of mines, and the notation is the same one the paper and README use.
// What the numbers mean, and that entropy is counted in bits, is help-pane
// material (static/help/mine-counter and static/help/entanglement), reached by
// the help-id attributes below. Screen readers get the full wording from the
// .sr-only span, since an icon and a bare number would otherwise be read as an
// unlabelled figure.
function renderStatus(state) {
  const host = document.getElementById("status-bar");
  if (!host) return;
  const mineValue = state.mines_exp.toFixed(1);
  const entValue = String(Math.trunc(state.ent_measure)); // trunc matches the old "%d"
  const mineLabel = `${mineValue} expected mines`;
  const entLabel = `${entValue} bits of entanglement`;
  // If the bar already exists, just update the numbers in place. That keeps the
  // existing <td> elements (and the help-id listeners help.js attached to them on
  // load) alive across a no-reload re-render. Otherwise build it from scratch.
  const mineCell = host.querySelector(".mine-counter");
  const entCell = host.querySelector(".entanglement");
  if (mineCell && entCell) {
    mineCell.querySelector(".status-value").textContent = mineValue;
    mineCell.querySelector(".sr-only").textContent = mineLabel;
    entCell.querySelector(".status-value").textContent = entValue;
    entCell.querySelector(".sr-only").textContent = entLabel;
    return;
  }
  const counter = (cls, helpId, tooltip, icon, value, label) =>
    el("div", { class: `status-counter ${cls}`, "help-id": helpId, title: tooltip }, [
      icon,
      el("span", { class: "status-value", text: value }),
      el("span", { class: "sr-only", text: label }),
    ]);
  // The two counters sit together above the board rather than at the page
  // edges: they are small enough to read as one scoreboard, and the right edge
  // is where the help sidebar opens over the page.
  host.replaceChildren(
    el("div", { class: "status-row" }, [
      counter(
        "mine-counter", "mine-counter", "Expected number of mines",
        el("span", { class: "status-icon", text: "⟨💣⟩ =", "aria-hidden": "true" }),
        mineValue, mineLabel
      ),
      counter(
        "entanglement", "entanglement", "Entanglement in bits: each cell, added up",
        el("span", { class: "status-icon", "aria-hidden": "true" }, [entanglementIcon(), " ="]),
        entValue, entLabel
      ),
    ])
  );
}

// --- Board: a <table> of cell buttons, one per grid entry.
function renderBoard(state) {
  const host = document.getElementById("board-container");
  if (!host) return;
  const ongoing = state.status === "ONGOING";
  const table = el("table", { class: "board" });
  for (let r = 0; r < state.rows; r++) {
    const tr = el("tr");
    for (let c = 0; c < state.cols; c++) {
      const val = state.grid[r][c];
      const decoded = decodeCell(val);
      const { text, cls, color } = decoded;
      const index = r * state.cols + c;
      const btn = el("button", {
        class: "tile " + cls,
        text,
        "aria-label": cellAriaLabel(r, c, val, decoded),
        "data-cell-index": index,
      });
      const inA = _probeA.has(index);
      const inB = _probeB.has(index);
      btn.classList.toggle("probe-a", inA);
      btn.classList.toggle("probe-b", inB);
      const isAnchor = Boolean(_probeAnchor && _probeAnchor[0] === r && _probeAnchor[1] === c);
      btn.classList.toggle("probe-anchor", isAnchor);
      if (inA || inB) {
        btn.appendChild(el("span", { class: "probe-badge", text: inA ? "A" : "B", "aria-hidden": "true" }));
        btn.setAttribute("aria-label", `${btn.getAttribute("aria-label")}; region ${inA ? "A" : "B"}`);
      }
      if (isAnchor) btn.setAttribute("aria-label", `${btn.getAttribute("aria-label")}; selection anchor`);
      if (color) btn.style.color = color;
      // While the game is running, clicking a cell runs clickCell(r, c) (tools.js),
      // which turns the current tool + this cell into a move and submits it.
      // When the game is over, cells are disabled.
      if (_probeEdit) btn.addEventListener("click", (event) => editProbeCell(r, c, event));
      else if (ongoing) btn.addEventListener("click", () => clickCell(r, c));
      else btn.disabled = true;
      tr.appendChild(el("td", {}, [btn]));
    }
    table.appendChild(tr);
  }
  // While a region is being edited the board also listens for press-and-drag
  // rectangles. One delegated listener on the freshly built table covers every
  // tile, and it disappears with the table on the next render.
  if (_probeEdit) {
    table.classList.add("probe-selecting");
    table.addEventListener("pointerdown", onBoardPointerDown);
  }
  // Moves now go through the JS engine (fetch), so no hidden form is needed.
  host.replaceChildren(table);
}

function formatBits(value) {
  const amount = Number(value).toFixed(3).replace(/\.?0+$/, "");
  return `${amount} ${Number(amount) === 1 ? "bit" : "bits"}`;
}

function invalidateProbeRequest() {
  _probeRequest += 1;
}

async function refreshProbe() {
  invalidateProbeRequest();
  _probeResult = null;
  _probeError = null;
  renderProbePanel();
  if (!_config.entanglement_probes || _probeA.size === 0 || _mutationPending) return;
  const request = _probeRequest;
  const areaB = _config.two_area_probes && _probeB.size ? [..._probeB].sort((a, b) => a - b) : null;
  try {
    const result = await window.GameEngine.probe(
      _gameId, [..._probeA].sort((a, b) => a - b), areaB
    );
    if (request !== _probeRequest) return;
    _probeResult = result;
    renderProbePanel();
  } catch (err) {
    if (request !== _probeRequest) return;
    _probeError = err && err.message ? err.message : "Probe failed";
    renderProbePanel();
  }
}

function setProbeEdit(mode) {
  cancelDrag();
  _probeEdit = _probeEdit === mode ? null : mode;
  _probeAnchor = null;
  if (_probeEdit && window.cancelMovePick) window.cancelMovePick();
  if (_state) renderBoard(_state);
  renderProbePanel();
  const active = document.querySelector(`[data-probe-mode="${mode}"]`);
  if (active) active.focus();
  if (_probeEdit) {
    document.dispatchEvent(new CustomEvent("tool:selected", {
      detail: { toolId: "region-probe", helpId: "region-probe" },
    }));
  }
}

// --- Region selection gestures ----------------------------------------------
// Three gestures edit the active region, and all of them end in
// applyRegionEdit():
//   click           toggle the clicked cell,
//   press and drag  the rectangle between the pressed and released cells,
//   shift-click     the rectangle between the anchor and the clicked cell.
// The anchor is the last cell toggled by a plain click (drawn with a dashed
// outline). Shift-click keeps rectangles available without a pointer, so
// keyboard users are not limited to one cell at a time.

// Every index inside the rectangle spanned by two [row, col] corners, in any
// corner order.
function rectangleIndices(from, to) {
  const indices = [];
  for (let r = Math.min(from[0], to[0]); r <= Math.max(from[0], to[0]); r++) {
    for (let c = Math.min(from[1], to[1]); c <= Math.max(from[1], to[1]); c++) {
      indices.push(r * _state.cols + c);
    }
  }
  return indices;
}

// Add the cells to the region being edited, or remove them from it. Regions A
// and B must stay disjoint, so adding a cell drops it from the other region.
function applyRegionEdit(indices, remove) {
  const region = _probeEdit === "A" ? _probeA : _probeB;
  const other = region === _probeA ? _probeB : _probeA;
  for (const index of indices) {
    if (remove) region.delete(index);
    else {
      other.delete(index);
      region.add(index);
    }
  }
}

function tileAt(index) {
  return document.querySelector(`#board-container [data-cell-index="${index}"]`);
}

function focusCell(cell) {
  const tile = tileAt(cell[0] * _state.cols + cell[1]);
  if (tile) tile.focus();
}

// Outline the rectangle the pointer is currently spanning. This only toggles
// classes on the affected tiles: rebuilding the whole board on every pointer
// move would be far too much work for a 375-cell preset.
function showPreview(indices, remove) {
  const next = new Set(indices);
  for (const index of _previewCells) {
    if (next.has(index)) continue;
    const tile = tileAt(index);
    if (tile) tile.classList.remove("probe-preview", "probe-preview-remove");
  }
  for (const index of next) {
    const tile = tileAt(index);
    if (!tile) continue;
    tile.classList.add("probe-preview");
    tile.classList.toggle("probe-preview-remove", remove);
  }
  _previewCells = next;
}

// Which cell sits under the pointer. Hit-testing by coordinate rather than by
// event.target is what makes touch work: after a touch pointerdown the browser
// retargets every later event of that pointer to the pressed tile, so
// event.target would never change during a finger drag.
function cellFromPoint(x, y) {
  const node = document.elementFromPoint ? document.elementFromPoint(x, y) : null;
  const tile = node && node.closest ? node.closest("[data-cell-index]") : null;
  if (!tile) return null;
  const index = Number(tile.getAttribute("data-cell-index"));
  if (!Number.isInteger(index)) return null;
  return [Math.floor(index / _state.cols), index % _state.cols];
}

function onBoardPointerDown(event) {
  if (!_state || !_probeEdit || _drag) return;
  if (event.button > 0) return;   // primary button (or touch/pen) only
  if (event.shiftKey) return;     // shift-click is handled as a click, not a drag
  const tile = event.target.closest ? event.target.closest("[data-cell-index]") : null;
  if (!tile) return;
  const index = Number(tile.getAttribute("data-cell-index"));
  const start = [Math.floor(index / _state.cols), index % _state.cols];
  const region = _probeEdit === "A" ? _probeA : _probeB;
  _drag = {
    pointerId: event.pointerId,
    start,
    end: start,
    moved: false,
    // Starting on a cell that is already in the region erases the rectangle
    // instead of drawing it, matching what a plain click on that cell does.
    remove: region.has(index),
  };
  _suppressClick = false;
  // The move and release can happen anywhere, including outside the board, so
  // the rest of the gesture is tracked on the document.
  document.addEventListener("pointermove", onDragMove);
  document.addEventListener("pointerup", onDragEnd);
  document.addEventListener("pointercancel", onDragCancel);
  document.addEventListener("keydown", onDragKey);
  updateDragPreview();
}

function onDragMove(event) {
  if (!_drag || (event.pointerId !== undefined && event.pointerId !== _drag.pointerId)) return;
  const cell = cellFromPoint(event.clientX, event.clientY);
  if (!cell) return; // pointer left the board: keep the last rectangle
  if (cell[0] === _drag.end[0] && cell[1] === _drag.end[1]) return;
  _drag.end = cell;
  if (cell[0] !== _drag.start[0] || cell[1] !== _drag.start[1]) _drag.moved = true;
  updateDragPreview();
}

function updateDragPreview() {
  const indices = rectangleIndices(_drag.start, _drag.end);
  showPreview(indices, _drag.remove);
  const rows = Math.abs(_drag.end[0] - _drag.start[0]) + 1;
  const cols = Math.abs(_drag.end[1] - _drag.start[1]) + 1;
  const verb = _drag.remove ? "remove from" : "add to";
  setProbeHint(`${rows} x ${cols} rectangle - release to ${verb} region ${_probeEdit}.`);
}

function onDragEnd(event) {
  if (!_drag || (event.pointerId !== undefined && event.pointerId !== _drag.pointerId)) return;
  const drag = _drag;
  endDrag();
  // A press that never left its tile is an ordinary click; let the click
  // handler toggle that one cell.
  if (!drag.moved) return;
  // A drag that returns to its starting tile still emits a click. Swallow it.
  _suppressClick = true;
  applyRegionEdit(rectangleIndices(drag.start, drag.end), drag.remove);
  _probeAnchor = drag.start;
  renderBoard(_state);
  focusCell(drag.end);
  refreshProbe();
}

function onDragKey(event) {
  if (event.key === "Escape") onDragCancel();
}

function onDragCancel() {
  if (!_drag) return;
  endDrag();
  renderProbePanel();
}

// Drop the in-progress rectangle and the listeners tracking it.
function endDrag() {
  document.removeEventListener("pointermove", onDragMove);
  document.removeEventListener("pointerup", onDragEnd);
  document.removeEventListener("pointercancel", onDragCancel);
  document.removeEventListener("keydown", onDragKey);
  _drag = null;
  showPreview([], false);
}

function cancelDrag() {
  if (_drag) endDrag();
}

function editProbeCell(row, col, event) {
  if (!_state || !_probeEdit) return;
  // Ignore the synthetic click a finished drag leaves behind. Keyboard
  // activation reports detail 0 and is never the tail of a drag, so it is
  // always allowed through.
  if (_suppressClick && (!event || event.detail !== 0)) {
    _suppressClick = false;
    return;
  }
  _suppressClick = false;
  const region = _probeEdit === "A" ? _probeA : _probeB;
  if (event && event.shiftKey && _probeAnchor) {
    applyRegionEdit(rectangleIndices(_probeAnchor, [row, col]), false);
  } else {
    const index = row * _state.cols + col;
    applyRegionEdit([index], region.has(index));
    _probeAnchor = [row, col]; // shift-click extends from the last plain click
  }
  renderBoard(_state);
  focusCell([row, col]);
  refreshProbe();
}

function clearProbes() {
  cancelDrag();
  invalidateProbeRequest();
  _probeA.clear();
  _probeB.clear();
  _probeEdit = null;
  _probeAnchor = null;
  _probeResult = null;
  _probeError = null;
  if (_state) renderBoard(_state);
  renderProbePanel();
}

function stopProbeEditing() {
  cancelDrag();
  if (!_probeEdit && !_probeAnchor) return;
  _probeEdit = null;
  _probeAnchor = null;
  if (_state) renderBoard(_state);
  renderProbePanel();
}

function probeButton(text, mode) {
  return el("button", {
    type: "button", class: `btn${_probeEdit === mode ? " active" : ""}`,
    text, "aria-pressed": _probeEdit === mode ? "true" : "false",
    "data-probe-mode": mode,
    onclick: () => setProbeEdit(mode),
  });
}

// Rewrite the editing hint alone. The drag preview updates on every pointer
// move, which is far too often to rebuild the panel (and would keep stealing
// focus from the buttons inside it).
function setProbeHint(text) {
  const hint = document.querySelector(".probe-hint");
  if (hint) hint.textContent = text;
}

function renderProbePanel() {
  const host = document.getElementById("probe-container");
  if (!host) return;
  if (!_config.entanglement_probes) {
    host.replaceChildren();
    return;
  }
  const controls = [probeButton("Edit A", "A")];
  if (_config.two_area_probes) controls.push(probeButton("Edit B", "B"));
  controls.push(el("button", { type: "button", class: "btn", text: "Clear regions", onclick: clearProbes }));

  const result = _probeResult;
  const error = _probeError;
  let primary = "Pick some cells for region A.";
  // The parts a two-region result is built from. What any of it *means* is
  // help-pane material (static/help/region-probe), not panel text.
  let breakdown = null;
  if (_mutationPending && _probeA.size) primary = "Waiting for the move to complete…";
  else if (_probeA.size && !result && !error) primary = "Calculating…";
  if (error) {
    primary = `Probe unavailable: ${error}`;
  } else if (result && _probeB.size && result.mutual_information !== null) {
    primary = `Shared information between A and B: ${formatBits(result.mutual_information)}`;
    breakdown = `S(A) ${formatBits(result.entropy_a)} · S(B) ${formatBits(result.entropy_b)} · S(A ∪ B) ${formatBits(result.entropy_union)}`;
  } else if (result) {
    primary = `Entanglement with the rest of the board: ${formatBits(result.entropy_a)}`;
  }
  host.replaceChildren(el("section", { class: "probe-panel", "help-id": "region-probe", "aria-label": "Entanglement probe" }, [
    el("h3", { text: "Entanglement probe" }),
    el("div", { class: "probe-controls" }, controls),
    // Only shown while editing; the drag preview rewrites this line in place.
    _probeEdit
      ? el("p", {
          class: "probe-hint",
          text: `Region ${_probeEdit}: click cells to add or remove them. Drag to draw a rectangle, or shift-click to stretch one from the dashed cell.`,
        })
      : null,
    el("p", { class: "probe-counts", text: `Region A: ${_probeA.size} cell${_probeA.size === 1 ? "" : "s"}${_config.two_area_probes ? ` · Region B: ${_probeB.size} cell${_probeB.size === 1 ? "" : "s"}` : ""}` }),
    el("p", { class: "probe-result", "aria-live": "polite", text: primary }),
    breakdown ? el("p", { class: "probe-breakdown", text: breakdown }) : null,
  ]));
}

// Which gate buttons appear, grouped into rows for layout. Ordering and row
// breaks are presentation choices, so they stay in JavaScript. Python remains
// authoritative for legality and arity; contract tests keep these rows aligned
// with the shared move definitions.
const TOOL_ROWS = {
  "core1": ["X", "Y", "Z", "H", "S"],
  "full1": ["SDG", "SX", "SXDG", "SY", "SYDG"],
  "two": ["CX", "SWAP"],
  "twoext": ["CX", "CY", "CZ", "SWAP"]
};

const TOOL_LABELS = {
  M: "Measure cell",
  P: "Pin cell",
  X: "Apply X gate",
  Y: "Apply Y gate",
  Z: "Apply Z gate",
  H: "Apply H gate",
  S: "Apply S gate",
  SDG: "Apply S dagger gate",
  SX: "Apply square-root X gate",
  SXDG: "Apply square-root X dagger gate",
  SY: "Apply square-root Y gate",
  SYDG: "Apply square-root Y dagger gate",
  CX: "Apply controlled X gate",
  CY: "Apply controlled Y gate",
  CZ: "Apply controlled Z gate",
  SWAP: "Apply SWAP gate",
};

// One tool button. Clicking it selects that tool (setTool, in tools.js).
function toolButton(token, helpId) {
  const label = TOOL_LABELS[token] || `Select ${token}`;
  const arity = _config.gate_arities && _config.gate_arities[token];
  return el("button", {
    type: "button",
    class: "btn tool",
    "help-id": helpId,
    "aria-label": label,
    title: label,
    "data-tool-id": token,
    "data-arity": arity,
    text: token,
    onclick: () => setTool(token),
  });
}

// --- Tools ("Select Move"): Measure/Pin plus the gates allowed by the move set.
function renderTools(state) {
  const host = document.getElementById("tools-container");
  if (!host) return;
  // The tool set only changes when the game ends or the move set changes — never
  // on an ordinary move. Skip rebuilding when it's unchanged so the existing
  // buttons keep their active highlight (set by tools.js) and their help-id
  // listeners (attached by help.js on load).
  const sig = state.status === "ONGOING" ? state.moveset : "OVER";
  if (sig === _toolsSig) return;
  _toolsSig = sig;
  if (state.status !== "ONGOING") {
    host.replaceChildren(); // game over -> no tools
    return;
  }
  const tools = el("div", { class: "tools" });
  // Measure + Pin are always available.
  tools.appendChild(el("div", { class: "tool-row" }, [toolButton("M", "M-move"), toolButton("P", "P-move")]));
  // Build a row of gate buttons from a list of tokens.
  const row = (gates) => el("div", { class: "tool-row" }, gates.map((t) => toolButton(t, t + "-gate")));
  const ms = state.moveset;
  if (["ONE_QUBIT", "ONE_QUBIT_COMPLETE", "TWO_QUBIT", "TWO_QUBIT_EXTENDED"].includes(ms)) tools.appendChild(row(TOOL_ROWS.core1));
  if (["ONE_QUBIT_COMPLETE", "TWO_QUBIT_EXTENDED"].includes(ms)) tools.appendChild(row(TOOL_ROWS.full1));
  if (ms === "TWO_QUBIT") tools.appendChild(row(TOOL_ROWS.two));
  if (ms === "TWO_QUBIT_EXTENDED") tools.appendChild(row(TOOL_ROWS.twoext));
  host.replaceChildren(
    el("h3", { text: "Select Move" }),
    tools,
    el("p", {
      id: "tool-hint",
      class: "tool-hint",
      "aria-live": "polite",
      text: "Measure selected: choose a cell.",
    })
  );
}

// Whether to show the "Reset Board" button, per the server's reset policy
// ("any" = always, "sandbox" = only in Sandbox games, "never" = hidden).
function resetAllowed(state, config) {
  const rp = config.reset_policy;
  return rp === "any" || (rp === "sandbox" && state.win_condition === "SANDBOX");
}

// The reset/new-game/new-setup form (a normal POST to /game, which reloads).
// Shown both while playing and on the game-over screen; on game-over it may also
// include a survey link.
function actionForm(state, config) {
  // Restarting (reset / new game / new setup) should drop back to the default
  // Measure tool. tools.js remembers the last tool in localStorage("qms_tool"),
  // so we clear it to "M" on click; the reloaded page then starts on Measure.
  const resetTool = () => localStorage.setItem("qms_tool", "M");
  const buttons = [];
  if (resetAllowed(state, config)) {
    buttons.push(el("button", { type: "submit", class: "btn", name: "action", value: "reset", text: "Reset Board", onclick: resetTool }));
  }
  buttons.push(el("button", { type: "submit", class: "btn", name: "action", value: "new_same", text: "New Game", onclick: resetTool }));
  buttons.push(el("button", { type: "submit", class: "btn", name: "action", value: "new_rules", text: "New Setup", onclick: resetTool }));
  if (state.status !== "ONGOING" && config.enable_survey && config.survey_url) {
    buttons.push(el("a", { class: "btn", href: config.survey_url, text: "Compile Survey" }));
  }
  return el("form", { class: "actions-form", action: `/game?game_id=${state.game_id}`, method: "post" }, [
    el("input", { type: "hidden", name: "game_id", value: state.game_id }),
    ...buttons, // spread the buttons array in as individual children
  ]);
}

// --- Actions: while playing, an "Actions" heading + the action form.
//     When the game is over, a "Game Over" overlay with a result message.
function renderActions(state, config) {
  const host = document.getElementById("actions-container");
  if (!host) return;
  if (state.status === "ONGOING") {
    host.replaceChildren(el("h3", { text: "Actions" }), actionForm(state, config));
    return;
  }
  const box = el("div", { class: "gameover-box" }, [el("h2", { text: "Game Over" })]);
  if (state.status === "WIN") {
    box.appendChild(el("div", { class: "result-icon", text: "🎉" }));
    const msg =
      state.win_condition === "CLEAR"
        ? "You cleared the board: every cell is safe to measure."
        : "You win!";
    box.appendChild(el("p", { class: "result-msg win", text: msg }));
  } else if (state.status === "LOST") {
    box.appendChild(el("div", { class: "result-icon", text: "💥" }));
    box.appendChild(el("p", { class: "result-msg lost", text: "A measurement observed a mine outcome." }));
  }
  box.appendChild(el("div", { class: "actions" }, [actionForm(state, config)]));
  host.replaceChildren(el("div", { class: "gameover-overlay" }, [box]));
}

// (Re)build every slot from a game-state object, using the cached config.
// Called once on load and again after each no-reload move (with fresh state).
function applyState(state) {
  const sameGame = _gameId === null || _gameId === state.game_id;
  cancelDrag();
  invalidateProbeRequest();
  if (!sameGame) {
    _probeA.clear();
    _probeB.clear();
    _probeEdit = null;
    _probeAnchor = null;
  }
  _state = state;
  _mutationPending = false;
  _gameId = state.game_id;
  renderStatus(state);
  renderBoard(state);
  renderTools(state);
  renderActions(state, _config);
  refreshProbe();
}

// Exposed so the move flow (tools.js) can re-render after the engine returns new
// state, and so it knows which game to send moves for. The browser-mode engine
// (Phase 2E) drives this exactly the same way.
window.GameRenderer = {
  applyState,
  gameId: () => _gameId,
  beforeMutation: () => {
    _mutationPending = true;
    invalidateProbeRequest();
    _probeResult = null;
    _probeError = null;
    renderProbePanel();
  },
  clearProbes,
  stopProbeEditing,
  mergeConfig: (config) => {
    _config = { ..._config, ...config };
    renderProbePanel();
  },
};

// Top-level on load: cache config, and build the initial view if state was
// inlined (server mode). In browser mode there is no inlined #game-state — the
// PyodideEngine produces the first state and browser-main.js calls applyState.
function render() {
  _config = readJson("app-config") || {};
  const state = readJson("game-state");
  if (state) applyState(state);
}

// Run as soon as the page's HTML is parsed. This <script> sits at the end of
// <body>, so by the time it runs the slots already exist and render() builds the
// view before the first paint (no flash of empty containers). The readyState
// check is a belt-and-braces fallback in case the script is ever loaded earlier.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", render);
} else {
  render();
}
