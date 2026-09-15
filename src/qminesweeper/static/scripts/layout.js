// Keep fixed desktop panels aligned with the bottom of the sticky application
// header. The header height is content- and width-dependent, so CSS must not
// guess it: translated labels and narrow screens can both change the real size.
(function () {
  const root = document.documentElement;
  const header = document.querySelector(".app-header");
  if (!root || !header) return;

  function publishHeaderSize() {
    root.style.setProperty("--app-header-block-size", `${header.offsetHeight}px`);
  }

  publishHeaderSize();
  window.addEventListener("resize", publishHeaderSize);

  // ResizeObserver catches changes that do not resize the viewport, including
  // font loading, translated text, and feature controls appearing in place.
  if (typeof ResizeObserver !== "undefined") {
    const observer = new ResizeObserver(publishHeaderSize);
    observer.observe(header);
  }
})();
