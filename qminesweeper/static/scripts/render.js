// static/scripts/render.js
//
// Client-side rendering of the game view from values the server emits as
// `data-*` attributes. The server provides game state (the grid encoding and
// observables); every presentation decision - symbols, state classes, clue
// colour, labels, number formatting - lives here.

function decodeCell(val) {
  if (val === -1) return { text: "■", cls: "unexplored", color: null };
  if (val === -2) return { text: "⚑", cls: "pinned", color: null };
  if (val === 9) return { text: "💥", cls: "mine", color: null };
  if (val === 0) return { text: "\u00a0", cls: "empty", color: null };
  // clue: 0 < val <= 8 (sum of neighbour mine probabilities)
  const v = Math.max(0.0, Math.min(val / 8.0, 1.0));
  const color = `rgb(${Math.round(255 * v)},${Math.round(255 * (1.0 - v))},0)`;
  return { text: val.toFixed(1), cls: "clue", color };
}

function renderCells() {
  document.querySelectorAll(".board .tile").forEach((el) => {
    const val = parseFloat(el.dataset.val);
    if (isNaN(val)) return;
    const { text, cls, color } = decodeCell(val);
    el.textContent = text;
    el.className = "tile " + cls;
    el.style.color = color || "";
  });
}

function renderStatus() {
  const mines = document.querySelector(".mine-counter");
  if (mines && mines.dataset.minesExp !== undefined) {
    mines.textContent = `⟨Mines⟩ = ${parseFloat(mines.dataset.minesExp).toFixed(1)}`;
  }
  const ent = document.querySelector(".entanglement");
  if (ent && ent.dataset.entMeasure !== undefined) {
    ent.textContent = `Entanglement = ${Math.trunc(parseFloat(ent.dataset.entMeasure))} bits`;
  }
}

function render() {
  renderCells();
  renderStatus();
}

// Runs synchronously when included at end of <body> (DOM already parsed),
// or waits for DOMContentLoaded otherwise - either way before first paint.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", render);
} else {
  render();
}
