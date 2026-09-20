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
  // Help starts closed until the player explicitly enables it. Preserve that
  // choice on later visits so the toggle and pane always agree.
  const savedOpen = localStorage.getItem(KEY);
  const wasOpen = savedOpen === "1";
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

    // --- The live Bloch sphere (trial) ---
    // When JS_BLOCH_SPHERE is on, a one-qubit gate's visual draws the gate's
    // effect with a live blochkit animation instead of the tracked,
    // LaTeX-rendered SVG. It is a deployment choice, not a player-facing toggle,
    // so the two renderers are never both on screen and there is no new control
    // in the panel. The SVGs stay tracked and are the default; nothing about
    // their path below changes when the flag is off.
    const BLOCH_SPHERE_ON = window.QMS_JS_BLOCH_SPHERE === true;
    // The topic whose content is on screen right now. The sphere is mounted after
    // an await, by which time the reader may have moved the pointer on, so this is
    // what says whether the work is still wanted. The DOM cannot answer that for a
    // topic like Measure, which has no node of its own to check for.
    let shownTopic = null;
    let blochModule = null; // the import() promise, kept so the module loads once
    let liveSphere = null; // the animation currently on screen, if any

    // The specifier has to be resolved to a full URL before import() sees it.
    // STATIC_BASE is "/static" on the server but a bare "static" in the browser
    // build, and a specifier that starts with neither "/" nor "./" is a *bare
    // module specifier* -- which a browser refuses to resolve at all, rather than
    // treating as a path. Resolving against document.baseURI covers both, and
    // keeps working if the build is ever served from a subdirectory.
    const blochUrl = new URL(`${STATIC_BASE}/scripts/bloch-help.js`, document.baseURI).href;
    const loadBloch = () => (blochModule ??= import(blochUrl));

    // A GateAnimation owns a requestAnimationFrame loop, and the panel throws its
    // own innerHTML away on every topic change. Without this the discarded SVG
    // would keep animating, invisibly, for the life of the page.
    function stopSphere() {
      if (liveSphere) {
        liveSphere.stop();
        liveSphere = null;
      }
    }

    /** Which ket the freshly injected SVG is already showing, e.g. `H_+.svg` -> "+". */
    function initialState(anim) {
      const m = /_([^_\/?]+)\.svg/.exec(anim.getAttribute("src") || "");
      if (!m) return null;
      try {
        return decodeURIComponent(m[1]);
      } catch {
        return m[1];
      }
    }

    // The six start states, spelled as blochkit names them. Only used to build a
    // selector for a topic that has no visual.html of its own; the gates ship their
    // own buttons, and those stay the source for them.
    const KETS = ["0", "1", "+", "-", "i", "-i"];

    /**
     * Build a visual from nothing, for a topic whose visual.html is empty.
     *
     * Measure is the case this exists for: it has never had an illustration, so
     * there is no image to stand down and no state buttons to listen to. The markup
     * matches what a gate's visual.html produces, so help.css styles both alike.
     */
    function buildLiveVisual(visualEl, caption) {
      const wrap = document.createElement("div");
      wrap.className = "gate-visual";

      const host = document.createElement("div");
      host.className = "bloch-stage";

      const p = document.createElement("p");
      p.textContent = caption;

      const selector = document.createElement("div");
      selector.className = "state-selector";
      for (const ket of KETS) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn";
        btn.dataset.state = ket;
        btn.textContent = `|${ket}⟩`;
        selector.appendChild(btn);
      }

      wrap.append(host, p, selector);
      visualEl.replaceChildren(wrap);
      return host;
    }

    /**
     * Draw this topic with the live sphere, if the flag is on and the topic is one
     * a Bloch sphere can show.
     *
     * `anim` is the topic's tracked SVG, or null when it has none. Failing quietly
     * is deliberate at every step: a topic with no sphere, a module that will not
     * load, or a panel that has moved on are all left with exactly what is already
     * on screen and working.
     */
    async function wireBlochSphere(visualEl, anim, id) {
      stopSphere(); // the previous topic's loop; its SVG has just been discarded
      if (!BLOCH_SPHERE_ON) return;

      const mod = await loadBloch().catch((err) => {
        console.warn("[help.js] Live Bloch sphere unavailable:", err);
        return null;
      });
      // Two-qubit gates and non-gate topics have no sphere. The topic check also
      // covers the panel having moved on while the module loaded, which the DOM
      // cannot answer for a topic that had no node of its own to begin with.
      if (!mod || !mod.canDraw(id) || shownTopic !== id) return;

      let host;
      if (anim) {
        host = document.createElement("div");
        host.className = "bloch-stage";
        anim.after(host);
        anim.hidden = true; // kept in the DOM: the state buttons still drive it
      } else {
        host = buildLiveVisual(visualEl, "Pick a starting state to see what this move does to it.");
      }

      // Built per topic: GateAnimation binds to the container it was given, and
      // that container is new every time the panel replaces its own innerHTML.
      liveSphere = new mod.GateSphere(host);
      liveSphere.show(id, (anim && initialState(anim)) || mod.defaultState(id));

      // For a gate these buttons already drive the (now hidden) SVG and this just
      // listens in; for a built visual they are ours and this is their only wiring.
      visualEl.querySelectorAll("button[data-state]").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (liveSphere) liveSphere.show(id, btn.dataset.state);
        });
      });
    }

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
      shownTopic = id;
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

      // With JS_BLOCH_SPHERE on, draw this topic live. Outside the `if` above
      // because `anim` may legitimately be null: Measure ships no SVG at all, and
      // the sphere is its first illustration. A no-op when the flag is off.
      wireBlochSphere(visualEl, anim, id);

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
