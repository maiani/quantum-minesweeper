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
// MOVES (for now): clicking a cell still submits a hidden <form> which reloads
// the whole page; the server then re-inlines fresh state and this script rebuilds
// the view. (Phase 2D will make moves update in place with no reload.)
//
// `clickCell` and `setTool` used below are defined in tools.js. They are only
// *called* later when the user clicks, by which time tools.js has loaded — so it
// is fine to reference them here.
// =============================================================================

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

// --- Status bar: "⟨Mines⟩ = X.X" on the left, "Entanglement = N bits" on the right.
// help-id attributes are picked up by help.js to show contextual help.
function renderStatus(state) {
  const host = document.getElementById("status-bar");
  if (!host) return;
  // replaceChildren(...) clears the slot and inserts the new content in one step.
  host.replaceChildren(
    el("table", { class: "status-table" }, [
      el("tr", {}, [
        el("td", {
          class: "mine-counter",
          "help-id": "mine-counter",
          text: `⟨Mines⟩ = ${state.mines_exp.toFixed(1)}`,
        }),
        el("td", { class: "status-spacer" }),
        el("td", {
          class: "entanglement",
          "help-id": "entanglement",
          text: `Entanglement = ${Math.trunc(state.ent_measure)} bits`, // trunc matches the old "%d"
        }),
      ]),
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
      const { text, cls, color } = decodeCell(state.grid[r][c]);
      const btn = el("button", { class: "tile " + cls, text });
      if (color) btn.style.color = color;
      // While the game is running, clicking a cell runs clickCell(r, c) (tools.js),
      // which turns the current tool + this cell into a move and submits it.
      // When the game is over, cells are disabled.
      if (ongoing) btn.addEventListener("click", () => clickCell(r, c));
      else btn.disabled = true;
      tr.appendChild(el("td", {}, [btn]));
    }
    table.appendChild(tr);
  }
  // Hidden form that tools.js's sendCmd() fills in and submits to POST /move.
  // (This is the current submit mechanism; it triggers a full page reload.)
  const form = el(
    "form",
    { id: "move-form", action: `/move?game_id=${state.game_id}`, method: "post", style: "display:none" },
    [
      el("input", { type: "hidden", name: "game_id", value: state.game_id }),
      el("input", { type: "hidden", id: "cmd-input", name: "cmd", value: "" }),
    ]
  );
  host.replaceChildren(table, form);
}

// Which gate buttons appear, grouped into rows for layout. This is a *curated*
// presentation list (a deliberate subset of what the rules allow — e.g. TWO_QUBIT
// intentionally offers only CX/SWAP), so it is decided here in the UI, keyed on
// the move set, rather than from the backend's allowed-moves.
const TOOL_ROWS = {
  core1: ["X", "Y", "Z", "H", "S"],
  full1: ["SDG", "SX", "SXDG", "SY", "SYDG"],
  two: ["CX", "SWAP"],
  twoext: ["CX", "CY", "CZ", "SWAP"],
};

// One tool button. Clicking it selects that tool (setTool, in tools.js).
function toolButton(token, helpId) {
  return el("button", {
    type: "button",
    class: "btn tool",
    "help-id": helpId,
    text: token,
    onclick: () => setTool(token),
  });
}

// --- Tools ("Select Move"): Measure/Pin plus the gates allowed by the move set.
function renderTools(state) {
  const host = document.getElementById("tools-container");
  if (!host) return;
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
  host.replaceChildren(el("h3", { text: "Select Move" }), tools);
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
  return el("form", { action: `/game?game_id=${state.game_id}`, method: "post" }, [
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

// Top-level: read the two JSON blobs and (re)build every slot of the view.
function render() {
  const state = readJson("game-state");
  if (!state) return; // not on the game page (or no state inlined)
  const config = readJson("app-config") || {};
  renderStatus(state);
  renderBoard(state);
  renderTools(state);
  renderActions(state, config);
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
