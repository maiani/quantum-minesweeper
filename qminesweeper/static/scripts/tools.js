// static/scripts/tools.js

let currentTool = localStorage.getItem("qms_tool") || "M";
let firstPick = null;

// Tool availability is whatever render.js put on screen for the current move
// set. Gate arity comes from each button's data-arity attribute, which render.js
// fills from the Python-owned app-config contract. This file therefore does not
// maintain another one-/two-qubit gate list.
function toolButtonFor(token) {
  return Array.from(document.querySelectorAll(".btn.tool")).find((button) => button.dataset.toolId === token) || null;
}

function currentGateArity() {
  const button = toolButtonFor(currentTool);
  if (!button || !button.dataset.arity) return null;
  return Number(button.dataset.arity);
}

// The entanglement probe's region editing is a selection mode just like Pin:
// while it is armed, clicking a cell edits a region instead of playing a move.
// render.js owns that state (it draws the regions and handles the clicks), so
// this file only asks whether it is on. One armed mode, one source of truth.
function activeProbeMode() {
  const renderer = window.GameRenderer;
  return renderer && renderer.probeMode ? renderer.probeMode() : null;
}

// Paint the tool row: nothing is highlighted while a probe region is armed,
// because the tool is not what the next cell click will do.
function syncToolSelection() {
  const probeMode = activeProbeMode();
  document.querySelectorAll(".btn.tool").forEach((button) => {
    const token = button.dataset.toolId || button.textContent;
    button.classList.toggle("active", !probeMode && token === currentTool);
  });
}

// Overwrite the hint line with one-off text (the probe's live drag readout).
// The next updateToolHint() call replaces it with the armed mode's own hint.
function setToolHint(text) {
  const hint = document.getElementById("tool-hint");
  if (hint) hint.textContent = text;
}

function updateToolHint() {
  const hint = document.getElementById("tool-hint");
  if (!hint) return;

  const probeMode = activeProbeMode();
  if (probeMode) {
    hint.textContent =
      `Region ${probeMode} selected: click cells to add or remove them. ` +
      "Drag to draw a rectangle, or shift-click to stretch one from the dashed cell.";
  } else if (currentTool === "M") {
    hint.textContent = "Measure selected: choose a cell.";
  } else if (currentTool === "P") {
    hint.textContent = "Pin selected: choose a cell to mark.";
  } else if (currentGateArity() === 1) {
    hint.textContent = `${currentTool} selected: choose one unexplored cell.`;
  } else if (currentGateArity() === 2 && firstPick) {
    hint.textContent = `${currentTool} selected: choose the target cell.`;
  } else if (currentGateArity() === 2) {
    hint.textContent = `${currentTool} selected: choose the first cell.`;
  } else {
    hint.textContent = "Choose a tool, then choose a cell.";
  }
}

function setTool(t) {
  // A persisted tool may not exist in a newly selected move set. Fall back to
  // Measure instead of retaining a hidden command that the rules will reject.
  if (!toolButtonFor(t) && toolButtonFor("M")) t = "M";
  currentTool = t;
  localStorage.setItem("qms_tool", t);
  firstPick = null;
  if (window.GameRenderer) window.GameRenderer.stopProbeEditing();

  // Active style
  syncToolSelection();
  document.querySelectorAll('.board button').forEach(b => b.classList.remove('pick'));

  announceTool();
  updateToolHint();
}

// Tell help.js which mode is now armed, so the help panel rests on its topic.
// Called when a tool is chosen and when a probe region is dropped, since the
// tool is what a cell click does again from then on.
function announceTool() {
  const el = document.querySelector('.btn.tool.active');
  if (!el) return;
  const toolId = el.dataset.toolId || el.textContent;
  const helpId = el.getAttribute("help-id");
  document.dispatchEvent(
    new CustomEvent("tool:selected", {
      detail: { toolId, helpId }
    })
  );
}

function cancelMovePick() {
  firstPick = null;
  document.querySelectorAll('.board button').forEach(b => b.classList.remove('pick'));
  updateToolHint();
}

// Submit a move command through the engine and re-render in place (no reload).
// engine.move() returns the new game state; GameRenderer.applyState() rebuilds
// the view from it. If the game has expired the server returns {redirect}; on a
// network error we fall back to a full reload (which lands back on a valid page).
function sendCmd(cmd) {
  const engine = window.GameEngine;
  const renderer = window.GameRenderer;
  if (!engine || !renderer) return; // engine.js / render.js not loaded
  // A probe is a read-only diagnostic, but its pending answer describes the
  // pre-move state. Invalidate it before starting any state mutation.
  renderer.beforeMutation();
  engine
    .move(renderer.gameId(), cmd)
    .then((state) => {
      if (!state) return;
      if (state.redirect) {
        window.location.href = state.redirect;
        return;
      }
      renderer.applyState(state);
    })
    .catch((err) => {
      console.error("move failed", err);
      window.location.reload();
    });
}

function clickCell(r, c) {
  const rc = `${r+1},${c+1}`;
  if (currentTool === 'M') { sendCmd(rc); return; }
  if (currentTool === 'P') { sendCmd(`P ${rc}`); return; }
  const arity = currentGateArity();
  if (arity === 1) { sendCmd(`${currentTool} ${rc}`); return; }
  if (arity === 2) {
    if (!firstPick) {
      firstPick = [r,c];
      // highlight the first pick
      const row = document.querySelectorAll('.board tr')[r];
      const btn = row.querySelectorAll('button')[c];
      btn.classList.add('pick');
      updateToolHint();
      return;
    } else {
      const [r1,c1] = firstPick;
      firstPick = null;
      // clear highlight from all buttons
      document.querySelectorAll('.board button').forEach(b => b.classList.remove('pick'));
      updateToolHint();
      const rc1 = `${r1+1},${c1+1}`;
      sendCmd(`${currentTool} ${rc1} ${rc}`);
    }
  }
}

// Exposed for render.js: arming or dropping a probe region changes which mode
// the tool row should show as active and what the shared hint line should say.
window.GameTools = {
  refresh: () => {
    syncToolSelection();
    updateToolHint();
  },
  setHint: setToolHint,
  announceTool,
};

// restore last selected tool on load
document.addEventListener("DOMContentLoaded", () => {
  setTool(currentTool);
});
if (document.readyState !== "loading") {
  setTool(currentTool);
}

// keyboard shortcuts
document.addEventListener("keydown", (event) => {
  const key = event.key.toUpperCase();

  if (key === "C") {
    document.addEventListener("keydown", function secondKey(ev) {
      const combo = "C" + ev.key.toUpperCase();
      if (toolButtonFor(combo)) {
        setTool(combo);
      }
    }, { once: true });
    return;
  }

  if (toolButtonFor(key)) {
    setTool(key);
  }
});
