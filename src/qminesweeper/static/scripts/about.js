// static/scripts/about.js
// =============================================================================
// Shared "About" overlay, used by BOTH the server pages and the static browser
// build.
//
// Why an overlay? About is a real page (/about on the server, about.html in the
// browser build) so it works with no JavaScript and stays crawlable for SEO. But
// *navigating* to it unloads the current page — which is expensive in the browser
// build, where it tears down the running Pyodide game and forces a multi-second
// reboot when the user comes back. So when JS is available we intercept the
// header's About link, fetch that page once, and show its content in an in-page
// overlay instead. The current page (and any running game) is left untouched.
//
// Progressive enhancement: if this script doesn't run, the link is a normal
// navigation to the About page, which still works.
// =============================================================================

(function () {
  const overlay = document.getElementById("about-overlay");
  if (!overlay) return;

  // Where the fetched About content gets injected, and whether we've loaded it yet
  // (we fetch only once, then reuse).
  const body = overlay.querySelector(".about-body");
  let loaded = false;

  function openOverlay() {
    overlay.hidden = false;
    // Lock background scroll while the modal is open (matters most on mobile).
    document.body.classList.add("overlay-open");
  }

  function closeOverlay() {
    overlay.hidden = true;
    document.body.classList.remove("overlay-open");
  }

  // Fetch the About page and lift just its content (.setup-expl) into the overlay.
  async function loadAbout(url) {
    try {
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      // Scope to <main>: the fetched page also contains this overlay's own (empty)
      // .setup-expl panel, so grab the real content from the page body, not that.
      const content = doc.querySelector("main .setup-expl");
      if (!content) throw new Error("no .setup-expl in About page");
      body.innerHTML = content.innerHTML;
      loaded = true;
      // The About text uses MathJax for quantum notation; typeset the new nodes.
      if (window.MathJax && window.MathJax.typesetPromise) {
        window.MathJax.typesetPromise([body]).catch(function () {});
      }
    } catch (err) {
      // Couldn't fetch (offline + uncached, etc.): fall back to a normal link so
      // the user can still reach the page.
      body.innerHTML =
        '<p>Unable to load the about page here. ' +
        '<a href="' + url + '">Open it directly</a>.</p>';
      console.warn("about overlay: load failed", err);
    }
  }

  // One delegated listener handles opening (header link), and closing (the ✕
  // button or a click on the backdrop outside the panel).
  document.addEventListener("click", function (event) {
    const target = event.target;
    if (!target || !target.closest) return;

    const aboutLink = target.closest('a[href$="/about"], a[href$="about.html"]');
    if (aboutLink) {
      event.preventDefault();
      openOverlay();
      if (!loaded) loadAbout(aboutLink.getAttribute("href"));
      return;
    }

    if (target.closest("[data-overlay-close]")) {
      closeOverlay();
      return;
    }
    // Click on the dim backdrop (the overlay itself, not the panel) closes it.
    if (target === overlay) closeOverlay();
  });

  // Escape closes the overlay when it's open.
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !overlay.hidden) closeOverlay();
  });
})();
