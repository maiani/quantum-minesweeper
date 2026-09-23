// static/scripts/theme_toggle.js
(function () {
  const KEY = 'qms_theme';
  // Cycle order for the button. Dark first because it is the shipped
  // default; retro last because it is the trial theme, not a co-equal third
  // option in the rotation's framing.
  const THEMES = ['dark', 'light', 'retro'];
  const ICONS = { dark: '🌙', light: '☀️', retro: '🕹️' };
  const LABELS = { dark: 'dark', light: 'light', retro: 'retro' };

  // Retro is the one theme with webfonts (see base.css and DESIGN.md), and
  // the other two must stay offline-complete, so the stylesheet is fetched
  // only once retro is actually selected, not unconditionally from <head>.
  // Three families, one request: Racing Sans One for the page title, Press
  // Start 2P for buttons (short text -- it is far too wide for paragraphs),
  // and VT323 for everything else, including the status counters' LCD
  // digits.
  const RETRO_FONT_ID = 'retro-font-stylesheet';
  const RETRO_FONT_URL = 'https://fonts.googleapis.com/css2?family=Racing+Sans+One&family=Press+Start+2P&family=VT323&display=swap';
  let retroFontRequested = false;
  function ensureRetroFont() {
    if (retroFontRequested || document.getElementById(RETRO_FONT_ID)) return;
    retroFontRequested = true;
    const link = document.createElement('link');
    link.id = RETRO_FONT_ID;
    link.rel = 'stylesheet';
    link.href = RETRO_FONT_URL;
    document.head.appendChild(link);
  }

  function applyTheme(mode) {
    if (!THEMES.includes(mode)) mode = 'dark';
    // One theme hook per non-default theme. <body> is deliberately not
    // marked: the pre-paint script in <head> cannot reach it, so a rule
    // keyed off it would apply a frame late on every load.
    document.documentElement.classList.toggle('light', mode === 'light');
    document.documentElement.classList.toggle('retro', mode === 'retro');
    if (mode === 'retro') ensureRetroFont();
    const btn = document.getElementById('toggle-theme');
    if (btn) {
      btn.textContent = ICONS[mode];
      btn.title = `Theme: ${LABELS[mode]} (click to change)`;
      btn.setAttribute('aria-label', btn.title);
    }
  }

  function currentTheme() {
    const html = document.documentElement;
    if (html.classList.contains('retro')) return 'retro';
    if (html.classList.contains('light')) return 'light';
    return 'dark';
  }

  function toggleTheme() {
    const next = THEMES[(THEMES.indexOf(currentTheme()) + 1) % THEMES.length];
    localStorage.setItem(KEY, next);
    applyTheme(next);
  }

  document.addEventListener('DOMContentLoaded', () => {
    // Just pick up what inline script set
    applyTheme(currentTheme());

    const btn = document.getElementById('toggle-theme');
    if (btn) btn.addEventListener('click', toggleTheme);
  });
})();
