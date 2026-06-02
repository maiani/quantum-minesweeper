// static/scripts/tools.js

const singleQ = new Set(['X','Y','Z','H','S','SDG','SX','SXDG','SY','SYDG']);
const twoQ    = new Set(['CX','CY','CZ','SWAP']);
const allTools = new Set(['M','P', ...singleQ, ...twoQ]);

let currentTool = localStorage.getItem("qms_tool") || "M";
let firstPick = null;

function updateToolHint() {
  const hint = document.getElementById("tool-hint");
  if (!hint) return;

  if (currentTool === "M") {
    hint.textContent = "Measure selected: choose a cell.";
  } else if (currentTool === "P") {
    hint.textContent = "Pin selected: choose a cell to mark.";
  } else if (singleQ.has(currentTool)) {
    hint.textContent = `${currentTool} selected: choose one unexplored cell.`;
  } else if (twoQ.has(currentTool) && firstPick) {
    hint.textContent = `${currentTool} selected: choose the target cell.`;
  } else if (twoQ.has(currentTool)) {
    hint.textContent = `${currentTool} selected: choose the first cell.`;
  } else {
    hint.textContent = "Choose a tool, then choose a cell.";
  }
}

function setTool(t) {
  currentTool = t;
  localStorage.setItem("qms_tool", t);
  firstPick = null;

  // Active style
  document.querySelectorAll('.btn.tool').forEach(b => {
    b.classList.toggle('active', b.textContent === t);
  });
  document.querySelectorAll('.board button').forEach(b => b.classList.remove('pick'));

  // --- Dispatch tool:selected for help.js ---
  const el = document.querySelector('.btn.tool.active');
  if (el) {
    const toolId = el.dataset.toolId || el.textContent;
    const helpId = el.getAttribute("help-id");
    document.dispatchEvent(
      new CustomEvent("tool:selected", {
        detail: { toolId, helpId }
      })
    );
  }

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
  if (singleQ.has(currentTool)) { sendCmd(`${currentTool} ${rc}`); return; }
  if (twoQ.has(currentTool)) {
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

// restore last selected tool on load
document.addEventListener("DOMContentLoaded", () => {
  setTool(currentTool);
});
if (document.readyState !== "loading") {
  setTool(currentTool);
}

// keyboard shortcuts
document.addEventListener("keydown", (event) => {
  let key = event.key.toUpperCase();

  if (key === "C") {
    document.addEventListener("keydown", function secondKey(ev) {
      const combo = "C" + ev.key.toUpperCase();
      if (allTools.has(combo)) {
        setTool(combo);
      }
    }, { once: true });
    return;
  }

  if (allTools.has(key)) {
    setTool(key);
  }
});
