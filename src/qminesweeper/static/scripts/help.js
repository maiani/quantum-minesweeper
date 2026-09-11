// static/scripts/help.js
(function () {
  if (!window.QMS_ENABLE_HELP) {
    console.info("Help is disabled; skipping help.js");
    return;
  }

  const PANEL_ID = "sidebar";
  const TOGGLE_ID = "toggle-help";
  const KEY = "qms_help_open";
  const TOOL_KEY = "qms_tool";
  const STATIC_BASE = (window.QMS_STATIC_BASE || "/static").replace(/\/$/, "");

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
    const sidebar = document.getElementById("sidebar");
    const titleEl = document.getElementById("help-title");
    const visualEl = document.getElementById("help-visual");
    const textEl = document.getElementById("help-text");
    const mountEl = document.getElementById("help-mount");

    if (!sidebar || !titleEl || !visualEl || !textEl) {
      console.warn("Help DOM not fully present; skipping content wiring");
      return;
    }

    // Preserve placement for mobile vs desktop
    const originalParent = sidebar.parentNode;
    const originalNext = sidebar.nextSibling;
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
      const base = `${STATIC_BASE}/help/${id}/`;

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
      textEl.innerHTML = HELP_CACHE[id].text;
      visualEl.innerHTML = HELP_CACHE[id].visual;
      visualEl.querySelectorAll('img[src^="/static/"]').forEach((img) => {
        img.src = img.getAttribute("src").replace(/^\/static/, STATIC_BASE);
      });

      // --- wire up the injected visual (compute template and attach handlers) ---
      const anim = visualEl.querySelector('#gate-animation');
      if (anim) {
        console.log("[help.js] Found #gate-animation:", anim);

        let template = anim.getAttribute('data-src-template');
        if (!template) {
          const srcAttr = anim.getAttribute('src') || '';
          const m = srcAttr.match(/^(.*_)[^_\/?]+(\.svg)(\?.*)?$/);
          if (m) {
            template = `${m[1]}{STATE}${m[2]}${m[3] || ''}`;
          } else {
            template = srcAttr.replace(/\.svg(\?.*)?$/, `_{STATE}.svg$1`);
          }
        }

        anim.dataset.srcTemplate = template;
        anim.dataset.originalSrc = anim.getAttribute('src') || '';
        console.log("[help.js] Using src template:", template);

        visualEl.querySelectorAll('button[data-state]').forEach(btn => {
          btn.type = btn.type || 'button';
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            const rawState = btn.dataset.state;
            const encoded = encodeURIComponent(rawState);
            const newSrc = (anim.dataset.srcTemplate || '').replace('{STATE}', encoded);
            console.log(`[help.js] Button clicked (state=${rawState}) → newSrc=${newSrc}`);

            if (!newSrc) {
              console.error('[help.js] No image template available to construct src');
              return;
            }

            anim.onerror = () => {
              console.error('[help.js] Failed to load image:', newSrc);
              if (anim.dataset.originalSrc) {
                console.log('[help.js] Restoring original src:', anim.dataset.originalSrc);
                anim.src = anim.dataset.originalSrc;
              }
            };

            anim.onload = () => {
              console.log('[help.js] Loaded image:', newSrc);
            };

            const bust = `?t=${Date.now()}`;
            anim.src = newSrc + bust;
          });
        });
      }

      if (window.MathJax) {
        if (typeof MathJax.typesetPromise === "function") {
          MathJax.typesetPromise();
        } else if (window.MathJax.Hub && typeof window.MathJax.Hub.Queue === "function") {
          MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
        }
      }
    }

    // --- Attach listeners ---
    // The last help topic a button *activated*, which hovering only borrows:
    // moving off a hovered element returns the panel to this topic.
    let activeHelpId = null;
    // The [help-id] element the pointer is currently inside, so a move within
    // one element (say from the mine emoji to its number) is not a new hover.
    let hoveredOwner = null;

    // Both listeners are on `document` and find their target with closest(),
    // rather than being attached to each [help-id] element on load. That is
    // what makes contextual help work for parts of the page JavaScript draws
    // later or redraws: the status counters and probe row (rendered from game
    // state, and in the browser build only once Pyodide has booted), the tool
    // buttons, and the board. Elements bound individually at load time would
    // lose their help the moment they were replaced.
    //
    // mouseover/mouseout bubble, unlike mouseenter/mouseleave, so one listener
    // sees every crossing. Entering and leaving are the same event here: when
    // the pointer moves onto something that is not inside a [help-id] element,
    // `owner` is null and the panel goes back to the activated topic.
    document.addEventListener("mouseover", (event) => {
      // Moving into the panel itself must never change the topic: the pointer
      // goes there to scroll and read whatever is on screen, hovered or
      // activated. Without this the panel would swap back to the activated
      // topic the moment the pointer crossed into it, making any hovered topic
      // unreadable past its first screenful.
      if (event.target.closest && event.target.closest(`#${PANEL_ID}`)) return;
      const owner = event.target.closest ? event.target.closest("[help-id]") : null;
      if (owner === hoveredOwner) return;
      hoveredOwner = owner;
      if (!panel.classList.contains("active")) return;
      const id = owner && owner.getAttribute("help-id");
      if (id) loadHelp(id);
      else if (activeHelpId) loadHelp(activeHelpId);
    });

    document.addEventListener("click", (event) => {
      const owner = event.target.closest ? event.target.closest("[help-id]") : null;
      if (!owner) return;
      const id = owner.getAttribute("help-id");
      if (!id) return;
      // A button's help stays up after the pointer leaves; anything else is
      // only shown while help mode is on, matching its hover behaviour.
      if (owner.tagName === "BUTTON" || owner.classList.contains("tool-btn")) {
        activeHelpId = id;
        loadHelp(id);
      } else if (panel.classList.contains("active")) {
        loadHelp(id);
      }
    });

    if (wasOpen) {
      const currentTool = (localStorage.getItem(TOOL_KEY) || "").toUpperCase();
      if (currentTool === "M" || currentTool === "P") {
        loadHelp(currentTool + "-move");
      } else {
        loadHelp(currentTool + "-gate");
      }
    }
    // Arming a mode — a gate, Measure, Pin, or a probe region — is an
    // activation, so its topic becomes the one hovering returns to. Region
    // buttons carry their help on the surrounding panel rather than on
    // themselves, so the click listener above cannot make them sticky.
    document.addEventListener("tool:selected", (e) => {
      const { helpId } = e.detail;
      if (helpId) {
        activeHelpId = helpId;
        loadHelp(helpId);
      }
    });
  });
})();
