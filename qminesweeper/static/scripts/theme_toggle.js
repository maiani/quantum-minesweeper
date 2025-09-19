// static/scripts/theme_toggle.js
(function () {
  const KEY = 'qms_theme';

  function applyTheme(mode) {
    const isLight = mode === 'light';
    document.documentElement.classList.toggle('light', isLight);
    document.body.classList.toggle('light', isLight);
    const btn = document.getElementById('toggle-theme');
    if (btn) btn.textContent = isLight ? '☀️' : '🌙';
  }

  function toggleTheme() {
    const next = document.documentElement.classList.contains('light') ? 'dark' : 'light';
    localStorage.setItem(KEY, next);
    applyTheme(next);
  }

  document.addEventListener('DOMContentLoaded', () => {
    // Just pick up what inline script set
    const isLight = document.documentElement.classList.contains('light');
    applyTheme(isLight ? 'light' : 'dark');

    const btn = document.getElementById('toggle-theme');
    if (btn) btn.addEventListener('click', toggleTheme);
  });
})();
