// static/scripts/theme_toggle.js
(function () {
  const KEY = 'qms_theme';

  function applyTheme(mode) {
    const isLight = mode === 'light';
    // One theme hook. <body> is deliberately not marked: the pre-paint script
    // in <head> cannot reach it, so a rule keyed off body.light would apply a
    // frame late on every load.
    document.documentElement.classList.toggle('light', isLight);
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
