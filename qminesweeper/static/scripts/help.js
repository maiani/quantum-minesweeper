// static/scripts/help.js
(function () {
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

  // --- Restore saved state ---
  const wasOpen = localStorage.getItem(KEY) === "1";
  panel.classList.toggle("active", wasOpen);
  panel.setAttribute("aria-hidden", wasOpen ? "false" : "true");
  if (toggleBtn) {
    toggleBtn.classList.toggle("active", wasOpen);
    toggleBtn.setAttribute("title", wasOpen ? "Help mode is ON" : "Click to enable Help mode");
  }

  // --- Toggle button ---
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const active = panel.classList.toggle("active");
      panel.setAttribute("aria-hidden", active ? "false" : "true");
      localStorage.setItem(KEY, active ? "1" : "0");
      toggleBtn.classList.toggle("active", active);
      toggleBtn.setAttribute("title", active ? "Help mode is ON" : "Click to enable Help mode");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    const sidebar  = document.getElementById("sidebar");
    const titleEl  = document.getElementById("help-title");
    const visualEl = document.getElementById("help-visual");
    const textEl   = document.getElementById("help-text");
    const mountEl  = document.getElementById("help-mount");

    if (!sidebar || !titleEl || !visualEl || !textEl) {
      console.warn("Help DOM not fully present; skipping content wiring");
      return;
    }

    // Preserve placement for mobile vs desktop
    const originalParent = sidebar.parentNode;
    const originalNext   = sidebar.nextSibling;
    const mq = window.matchMedia("(max-width: 720px)");

    function mountInline(isInline) {
      const open = localStorage.getItem(KEY) === "1";
      if (isInline) {
        if (mountEl && sidebar.parentNode !== mountEl.parentNode) {
          mountEl.after(sidebar);
        }
        sidebar.classList.add("inline");
        sidebar.classList.toggle("active", open);
        sidebar.setAttribute("aria-hidden", open ? "false" : "true");
      } else {
        if (originalParent) {
          originalParent.insertBefore(sidebar, originalNext);
        }
        sidebar.classList.remove("inline");
        sidebar.classList.toggle("active", open);
        sidebar.setAttribute("aria-hidden", open ? "false" : "true");
      }
    }
    mountInline(mq.matches);
    mq.addEventListener("change", e => mountInline(e.matches));

    // --- Cache + loader ---
    const HELP_CACHE = {};
    async function loadHelp(id) {
      const base = `/static/help/${id}/`;

      if (!HELP_CACHE[id]) {
        try {
          const [textRes, visualRes] = await Promise.all([
            fetch(base + "text.html"),
            fetch(base + "visual.html"),
          ]);

          let textHtml = textRes.ok ? await textRes.text() : "<p>No description.</p>";
          let title = id;

          // Extract <h1> as title
          const tmp = document.createElement("div");
          tmp.innerHTML = textHtml;
          const h1 = tmp.querySelector("h1");
          if (h1) {
            title = h1.textContent.trim();
            h1.remove();
            textHtml = tmp.innerHTML;
          }

          HELP_CACHE[id] = {
            title,
            text: textHtml,
            visual: visualRes.ok ? await visualRes.text() : "<div></div>",
          };
        } catch {
          HELP_CACHE[id] = {
            title: id,
            text: "<p>No help available.</p>",
            visual: "<div></div>",
          };
        }
      }

      titleEl.textContent = HELP_CACHE[id].title;
      textEl.innerHTML    = HELP_CACHE[id].text;
      visualEl.innerHTML = HELP_CACHE[id].visual;

      // --- wire up the injected visual (compute template and attach handlers) ---
      const anim = visualEl.querySelector('#gate-animation');
      if (anim) {
        // prefer explicit template if visual.html provides it:
        // <img id="gate-animation" data-src-template="/static/help/H-gate/svgs/H_{STATE}.svg" src="...">
        let template = anim.getAttribute('data-src-template');

        // otherwise calculate a template from the declared src attribute (not .src)
        if (!template) {
          const srcAttr = anim.getAttribute('src') || '';
          // match "..._<token>.svg" (possibly followed by ?query). Capture prefix and suffix.
          const m = srcAttr.match(/^(.*_)[^_\/?]+(\.svg)(\?.*)?$/);
          if (m) {
            // prefix includes trailing underscore, suffix is ".svg" + optional query
            template = `${m[1]}{STATE}${m[2]}${m[3] || ''}`;
          } else {
            // fallback: replace the final ".svg" with "_{STATE}.svg"
            template = srcAttr.replace(/\.svg(\?.*)?$/, `_{STATE}.svg$1`);
          }
        }

        // store for later and preserve original src to restore on error
        anim.dataset.srcTemplate = template;
        anim.dataset.originalSrc = anim.getAttribute('src') || '';

        // attach button handlers (works with <button data-state="...">)
        visualEl.querySelectorAll('button[data-state]').forEach(btn => {
          // prevent accidental form submit
          btn.type = btn.type || 'button';
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            const rawState = btn.dataset.state;
            const encoded = encodeURIComponent(rawState);
            const newSrc = (anim.dataset.srcTemplate || '').replace('{STATE}', encoded);
            if (!newSrc) { console.error('No image template available to construct src'); return; }

            // restore original if load fails
            anim.onerror = () => {
              console.error('Failed to load image:', newSrc);
              // restore the original image (so UI doesn't remain blank)
              if (anim.dataset.originalSrc) anim.src = anim.dataset.originalSrc;
            };
            anim.onload = () => { console.log('Loaded image:', newSrc); };

            // optional cache-bust for debugging; remove "?t=..." in production
            anim.src = newSrc + `?t=${Date.now()}`;
            console.log('Requested', anim.src);
          });
        });

        // expose a simple global for inline onclick handlers if any visual files still use them:
        window.setState = function (st) {
          const encoded = encodeURIComponent(st);
          const newSrc = (anim.dataset.srcTemplate || '').replace('{STATE}', encoded);
          if (!newSrc) return console.error('setState: no template');
          anim.onerror = () => {
            console.error('setState failed to load', newSrc);
            if (anim.dataset.originalSrc) anim.src = anim.dataset.originalSrc;
          };
          anim.src = newSrc + `?t=${Date.now()}`;
        };
      }




      if (window.MathJax) MathJax.typesetPromise();
    }

    // --- Attach listeners ---
    let activeHelpId = null;

    // --- Attach listeners ---
    document.querySelectorAll("[help-id]").forEach(el => {
      const id = el.getAttribute("help-id");
      if (!id) return;

      const isButton = el.classList.contains("tool-btn") || el.tagName === "BUTTON";

      if (isButton) {
        // Buttons: activation only on click (no hover)
        el.addEventListener("click", () => {
          activeHelpId = id;
          loadHelp(id);
        });
      } else {
        // Non-buttons: keep hover (only when panel is active)...
        el.addEventListener("mouseenter", () => {
          if (panel.classList.contains("active")) loadHelp(id);
        });
        el.addEventListener("click", () => {
          if (panel.classList.contains("active")) loadHelp(id);
        });
        // ...and revert to last activated button help on mouseleave
        el.addEventListener("mouseleave", () => {
          if (panel.classList.contains("active") && activeHelpId) {
            loadHelp(activeHelpId);
          }
        });
      }
    });
  });
})();
