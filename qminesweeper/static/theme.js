// static/theme.js
(function () {
  const KEY = 'qms_theme';

  function applyTheme(mode) {
    const isLight = mode === 'light';
    // support both <html> and <body> for no-flash + runtime
    document.documentElement.classList.toggle('light', isLight);
    document.body.classList.toggle('light', isLight);
    const btn = document.getElementById('toggle-theme');
    if (btn) btn.textContent = isLight ? '☀️' : '🌙';
  }

  function initialTheme() {
    const saved = localStorage.getItem(KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    // fallback to system preference
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches)
      ? 'light' : 'dark';
  }

  function toggleTheme() {
    const next = document.documentElement.classList.contains('light') ? 'dark' : 'light';
    localStorage.setItem(KEY, next);
    applyTheme(next);
  }

  document.addEventListener('DOMContentLoaded', () => {
    // If an inline no-flash script set <html class="light">, honor it; else compute.
    const hasClass = document.documentElement.classList.contains('light');
    applyTheme(hasClass ? 'light' : initialTheme());

    const btn = document.getElementById('toggle-theme');
    if (btn) btn.addEventListener('click', toggleTheme);
  });
})();
