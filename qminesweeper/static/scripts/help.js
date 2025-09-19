// static/scripts/help.js

(function () {
  const PANEL_ID = "help-panel";
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