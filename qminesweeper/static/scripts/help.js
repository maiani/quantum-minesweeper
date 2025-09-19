// static/scripts/help.js
(function () {
  const PANEL_ID = "sidebar";
  const TOGGLE_ID = "toggle-help"; 
  const KEY = "qms_help_open";

  const panel = document.getElementById(PANEL_ID);
  const toggleBtn = document.getElementById(TOGGLE_ID);
  if (!panel || !toggleBtn) return;

  // Restore state
  if (localStorage.getItem(KEY) === "1") {
    panel.classList.add("active");
    panel.setAttribute("aria-hidden", "false");
  } else {
    panel.classList.remove("active");
    panel.setAttribute("aria-hidden", "true");
  }

  // Toggle on click
  toggleBtn.addEventListener("click", () => {
    const active = panel.classList.toggle("active");
    panel.setAttribute("aria-hidden", active ? "false" : "true");
    localStorage.setItem(KEY, active ? "1" : "0");
  });
})();

document.addEventListener("DOMContentLoaded", () => {
  const sidebar  = document.getElementById("sidebar");
  const titleEl  = document.getElementById("help-title");
  const visualEl = document.getElementById("help-visual");
  const textEl   = document.getElementById("help-text");

  const HELP_CACHE = {};

  async function fetchHelp(id) {
    if (!HELP_CACHE[id]) {
      try {
        const res = await fetch(`/help/${id}`);
        if (!res.ok) throw new Error("Not found");
        HELP_CACHE[id] = await res.json();
      } catch {
        HELP_CACHE[id] = {
          title: id,
          text: "<p>No help available.</p>",
          visual: "<div></div>",
        };
      }
    }
    return HELP_CACHE[id];
  }

  async function loadHelp(id) {
    const info = await fetchHelp(id);

    const title = info.title || id;
    titleEl.textContent = title;
    textEl.innerHTML    = info.text || "";
    visualEl.innerHTML  = info.visual || "";

    sidebar.setAttribute("aria-labelledby", "help-title");
    sidebar.classList.add("active");

    if (window.MathJax) MathJax.typesetPromise(); // re-render LaTeX
  }

  // Attach listeners
  document.querySelectorAll("[help-id]").forEach(el => {
    const id = el.getAttribute("help-id");

    // Hover shows help
    el.addEventListener("mouseenter", () => loadHelp(id));

    // Click locks sidebar (optional)
    el.addEventListener("click", () => loadHelp(id));
  });
});
