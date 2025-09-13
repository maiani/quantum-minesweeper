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