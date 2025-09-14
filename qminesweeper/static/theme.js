(function () {
  const KEY = 'qms_theme';

  function applyTheme(value) {
    // value: 'light' | 'dark'
    if (value === 'light') {
      document.body.classList.add('light');
    } else {
      document.body.classList.remove('light');
    }
  }

  function toggleTheme() {
    const cur = localStorage.getItem(KEY) || 'dark';
    const next = (cur === 'dark') ? 'light' : 'dark';
    localStorage.setItem(KEY, next);
    applyTheme(next);
  }

  document.addEventListener('DOMContentLoaded', () => {
    // initialize from storage (default: dark)
    applyTheme(localStorage.getItem(KEY) || 'dark');

    // wire the toggle button if present
    const btn = document.getElementById('toggle-theme');
    if (btn) {
      btn.addEventListener('click', toggleTheme);
    }
  });
})();

document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const btn = document.getElementById("toggle-theme");

  function updateIcon() {
    if (body.classList.contains("light")) {
      btn.textContent = "☀️";
    } else {
      btn.textContent = "🌙";
    }
  }

  btn.addEventListener("click", () => {
    body.classList.toggle("light");
    updateIcon();
    // Persist in localStorage so it survives reloads
    localStorage.setItem("theme", body.classList.contains("light") ? "light" : "dark");
  });

  // Load from localStorage if available
  const saved = localStorage.getItem("theme");
  if (saved) {
    body.classList.toggle("light", saved === "light");
  }
  updateIcon();
});
