
// static/scripts/clue_style.js

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tile.clue").forEach(el => {
    const val = parseFloat(el.dataset.val);
    if (!isNaN(val)) {
      const v = Math.max(0.0, Math.min(val / 8.0, 1.0));
      const r = Math.round(255 * v);
      const g = Math.round(255 * (1.0 - v));
      el.style.color = `rgb(${r},${g},0)`;
    }
  });
});
