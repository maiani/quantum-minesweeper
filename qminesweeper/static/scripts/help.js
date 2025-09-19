// static/scripts/help.js
(function () {
  if (!window.QMS_ENABLE_HELP) {
    console.info("Help is disabled; skipping help.js");
    return;
  }

  const PANEL_ID = "sidebar";
  const TOGGLE_ID = "toggle-help";
  const KEY = "qms_help_open";

  const panel = document.getElementById(PANEL_ID);
  const toggleBtn = document.getElementById(TOGGLE_ID);
  if (!panel) return;

  // Restore state
  const wasOpen = localStorage.getItem(KEY) === "1";
  if (wasOpen) {
    panel.classList.add("active");
    panel.setAttribute("aria-hidden", "false");
  } else {
    panel.classList.remove("active");
    panel.setAttribute("aria-hidden", "true");
  }

  // Toggle button (if present)
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const active = panel.classList.toggle("active");
      panel.setAttribute("aria-hidden", active ? "false" : "true");
      localStorage.setItem(KEY, active ? "1" : "0");
    });
  }

  // --- Help content logic ---
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
      // safeguard: only load if help is enabled AND panel is open
      const isOpen = sidebar.classList.contains("active");
      if (!isOpen) return;

      const info = await fetchHelp(id);
      const title = info.title || id;
      titleEl.textContent = title;
      textEl.innerHTML    = info.text || "";
      visualEl.innerHTML  = info.visual || "";

      sidebar.setAttribute("aria-labelledby", "help-title");

      if (window.MathJax) MathJax.typesetPromise();
    }

    // Attach listeners
    document.querySelectorAll("[help-id]").forEach(el => {
      const id = el.getAttribute("help-id");

      // Hover updates if panel open
      el.addEventListener("mouseenter", () => loadHelp(id));

      // Click can also update (if open)
      el.addEventListener("click", () => loadHelp(id));
    });
  });
})();
