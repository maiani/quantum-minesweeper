// static/scripts/help.js
(function () {
  // --- Hard safeguard: don't run if help is disabled ---
  if (!window.QMS_ENABLE_HELP) {
    console.info("Help is disabled; skipping help.js");
    return;
  }

  const PANEL_ID = "sidebar";
  const TOGGLE_ID = "toggle-help";
  const KEY = "qms_help_open";

  const panel = document.getElementById(PANEL_ID);
  const toggleBtn = document.getElementById(TOGGLE_ID);
  if (!panel) {
    console.warn("Help panel element not found; skipping help.js");
    return;
  }

  // Restore state (will be re-applied after inline/desktop mount)
  const wasOpen = localStorage.getItem(KEY) === "1";
  panel.classList.toggle("active", wasOpen);
  panel.setAttribute("aria-hidden", wasOpen ? "false" : "true");

  // Toggle button: works in both desktop and inline/mobile modes
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const active = panel.classList.toggle("active");
      panel.setAttribute("aria-hidden", active ? "false" : "true");
      localStorage.setItem(KEY, active ? "1" : "0");
    });
  }

  // --- Help content + responsive (inline) mounting ---
  document.addEventListener("DOMContentLoaded", () => {
    const sidebar  = document.getElementById("sidebar");
    const titleEl  = document.getElementById("help-title");
    const visualEl = document.getElementById("help-visual");
    const textEl   = document.getElementById("help-text");
    const mountEl  = document.getElementById("help-mount"); // marker between Tools and Actions

    if (!sidebar || !titleEl || !visualEl || !textEl) {
      console.warn("Help DOM not fully present; skipping content wiring");
      return;
    }

    // Keep references to restore desktop placement
    const originalParent = sidebar.parentNode;
    const originalNext   = sidebar.nextSibling;

    const HELP_CACHE = {};
    const mq = window.matchMedia("(max-width: 720px)");

    function mountInline(isInline) {
      const open = localStorage.getItem(KEY) === "1";

      if (isInline) {
        // Move below tools (after #help-mount marker)
        if (mountEl && sidebar.parentNode !== mountEl.parentNode) {
          mountEl.after(sidebar);
        }
        sidebar.classList.add("inline");
        sidebar.classList.toggle("active", open);              // respect saved state
        sidebar.setAttribute("aria-hidden", open ? "false" : "true");
      } else {
        // Restore to original DOM position
        if (originalParent) {
          originalParent.insertBefore(sidebar, originalNext);
        }
        sidebar.classList.remove("inline");
        sidebar.classList.toggle("active", open);
        sidebar.setAttribute("aria-hidden", open ? "false" : "true");
      }
    }

    // Initial mount + react to resize
    mountInline(mq.matches);
    mq.addEventListener("change", e => mountInline(e.matches));

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
      titleEl.textContent = info.title || id;
      textEl.innerHTML    = info.text || "";
      visualEl.innerHTML  = info.visual || "";

      // Auto-open on use in both modes and remember it
      if (!sidebar.classList.contains("active")) {
        sidebar.classList.add("active");
        sidebar.setAttribute("aria-hidden", "false");
        localStorage.setItem(KEY, "1");
      }

      if (window.MathJax) MathJax.typesetPromise();
    }

    // Attach listeners to elements with help-id
    document.querySelectorAll("[help-id]").forEach(el => {
      const id = el.getAttribute("help-id");
      if (!id) return;
      el.addEventListener("mouseenter", () => loadHelp(id));
      el.addEventListener("click", () => loadHelp(id));
    });
  });
})();
