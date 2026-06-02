// static/scripts/render.js
//
// Builds the entire game view in JS from the inlined game-state JSON
// (<script id="game-state">). The server computes game state only; every
// presentation decision — symbols, classes, clue colour, labels, which tool
// buttons to show, action buttons — lives here.
//
// Move submission is still the hidden form + full reload (tools.js); on each
// reload the server re-inlines fresh state and this rebuilds the view.

function readState() {
  const el = document.getElementById("game-state");
  if (!el) return null;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return null;
  }
}

// Tiny DOM builder: el("button", {class, text, onclick, ...attrs}, [children])
function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === null || v === undefined) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "onclick") node.addEventListener("click", v);
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

// grid encoding -> appearance (the only place sentinels are decoded)
function decodeCell(val) {
  if (val === -1) return { text: "■", cls: "unexplored", color: null };
  if (val === -2) return { text: "⚑", cls: "pinned", color: null };
  if (val === 9) return { text: "💥", cls: "mine", color: null };
  if (val === 0) return { text: " ", cls: "empty", color: null };
  const v = Math.max(0.0, Math.min(val / 8.0, 1.0));
  const color = `rgb(${Math.round(255 * v)},${Math.round(255 * (1.0 - v))},0)`;
  return { text: val.toFixed(1), cls: "clue", color };
}

function renderStatus(state) {
  const host = document.getElementById("status-bar");
  if (!host) return;
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
          text: `Entanglement = ${Math.trunc(state.ent_measure)} bits`,
        }),
      ]),
    ])
  );
}

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
      if (ongoing) btn.addEventListener("click", () => clickCell(r, c));
      else btn.disabled = true;
      tr.appendChild(el("td", {}, [btn]));
    }
    table.appendChild(tr);
  }
  // hidden move form used by tools.js sendCmd()
  const form = el("form", { id: "move-form", action: `/move?game_id=${state.game_id}`, method: "post", style: "display:none" }, [
    el("input", { type: "hidden", name: "game_id", value: state.game_id }),
    el("input", { type: "hidden", id: "cmd-input", name: "cmd", value: "" }),
  ]);
  host.replaceChildren(table, form);
}

const TOOL_ROWS = {
  core1: ["X", "Y", "Z", "H", "S"],
  full1: ["SDG", "SX", "SXDG", "SY", "SYDG"],
  two: ["CX", "SWAP"],
  twoext: ["CX", "CY", "CZ", "SWAP"],
};

function toolButton(t, helpId) {
  return el("button", { type: "button", class: "btn tool", "help-id": helpId, text: t, onclick: () => setTool(t) });
}

function renderTools(state) {
  const host = document.getElementById("tools-container");
  if (!host) return;
  if (state.status !== "ONGOING") {
    host.replaceChildren();
    return;
  }
  const tools = el("div", { class: "tools" });
  tools.appendChild(el("div", { class: "tool-row" }, [toolButton("M", "M-move"), toolButton("P", "P-move")]));
  const ms = state.moveset;
  const row = (gates) => el("div", { class: "tool-row" }, gates.map((t) => toolButton(t, t + "-gate")));
  if (["ONE_QUBIT", "ONE_QUBIT_COMPLETE", "TWO_QUBIT", "TWO_QUBIT_EXTENDED"].includes(ms)) tools.appendChild(row(TOOL_ROWS.core1));
  if (["ONE_QUBIT_COMPLETE", "TWO_QUBIT_EXTENDED"].includes(ms)) tools.appendChild(row(TOOL_ROWS.full1));
  if (ms === "TWO_QUBIT") tools.appendChild(row(TOOL_ROWS.two));
  if (ms === "TWO_QUBIT_EXTENDED") tools.appendChild(row(TOOL_ROWS.twoext));
  host.replaceChildren(el("h3", { text: "Select Move" }), tools);
}

function resetAllowed(state) {
  const rp = state.features.reset_policy;
  return rp === "any" || (rp === "sandbox" && state.win_condition === "SANDBOX");
}

function actionForm(state) {
  const buttons = [];
  if (resetAllowed(state)) {
    buttons.push(el("button", { type: "submit", class: "btn", name: "action", value: "reset", text: "Reset Board" }));
  }
  buttons.push(el("button", { type: "submit", class: "btn", name: "action", value: "new_same", text: "New Game" }));
  buttons.push(el("button", { type: "submit", class: "btn", name: "action", value: "new_rules", text: "New Setup" }));
  if (state.status !== "ONGOING" && state.features.enable_survey && state.features.survey_url) {
    buttons.push(el("a", { class: "btn", href: state.features.survey_url, text: "Compile Survey" }));
  }
  return el("form", { action: `/game?game_id=${state.game_id}`, method: "post" }, [
    el("input", { type: "hidden", name: "game_id", value: state.game_id }),
    ...buttons,
  ]);
}

function renderActions(state) {
  const host = document.getElementById("actions-container");
  if (!host) return;
  if (state.status === "ONGOING") {
    host.replaceChildren(el("h3", { text: "Actions" }), actionForm(state));
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
  box.appendChild(el("div", { class: "actions" }, [actionForm(state)]));
  host.replaceChildren(el("div", { class: "gameover-overlay" }, [box]));
}

function render() {
  const state = readState();
  if (!state) return;
  renderStatus(state);
  renderBoard(state);
  renderTools(state);
  renderActions(state);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", render);
} else {
  render();
}
