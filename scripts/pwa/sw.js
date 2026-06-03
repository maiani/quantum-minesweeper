// =============================================================================
// Service worker for the Quantum Minesweeper PWA (browser-only build).
//
// Lives at the dist ROOT so its scope covers the whole app (index.html,
// about.html, /static, /py, and the cross-origin Pyodide CDN files).
//
// Strategy: split by origin so a stale app shell is structurally impossible.
//   - SAME-ORIGIN (our HTML/JS/CSS, modules.json, the .py engine, icons):
//       NETWORK-FIRST. When online you ALWAYS get the freshly-served file; the
//       cache is only a fallback for offline. This is what kills the "stuck on an
//       old build" class of bug for good — fresh code wins every time you're online.
//   - CROSS-ORIGIN (Pyodide + numpy from the jsDelivr CDN):
//       CACHE-FIRST. These are large and URL-versioned (immutable), so serving
//       them from cache is both correct and fast, and gives full offline play.
//
// Lifecycle:
//   - install  : pre-cache the tiny app shell so the app can open with no network
//   - activate : drop old-build caches, claim clients, and RELOAD them (self-heal)
//
// The cache name still carries the package version + a content fingerprint
// (stamped by build_browser.py), so each changed bundle gets a fresh cache and
// the old one is dropped in `activate`. With network-first that's now a belt-and-
// suspenders backup rather than the only line of defence.
// =============================================================================

const CACHE = "qms-pwa-__QMS_VERSION__";

// App shell: just enough to open offline. Everything else (CSS, JS, the Python
// engine modules, Pyodide, numpy) is cached lazily on first use by the fetch
// handler, so this list never needs to track the full asset set.
const CORE = ["./", "index.html", "about.html", "manifest.webmanifest"];

self.addEventListener("install", (event) => {
  // Pre-cache the shell, then take over without waiting for old tabs to close.
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(CORE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  // Self-heal on update: (1) drop every cache from a previous build so no stale
  // asset can survive, (2) take control of open pages, then (3) reload those
  // pages so they re-fetch their scripts through THIS worker. Without the reload,
  // an already-open tab keeps running the old in-memory script until the user
  // manually reloads — which is exactly the "cleared everything but still stale"
  // trap. The cache name carries the build fingerprint, so this whole block runs
  // once per changed build and then never again (no reload loop).
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
      await self.clients.claim();
      const windows = await self.clients.matchAll({ type: "window" });
      for (const client of windows) {
        // navigate() reloads the client under the new worker. Guard for older
        // engines that lack it; fire-and-forget so one failure can't block.
        if ("navigate" in client) client.navigate(client.url).catch(() => {});
      }
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  // Only GETs are cacheable; let POST/PUT/etc. (none in browser mode) pass through.
  if (req.method !== "GET") return;
  // Skip non-http(s) schemes (e.g. chrome-extension://) — caches.put rejects them.
  const url = new URL(req.url);
  if (url.protocol !== "http:" && url.protocol !== "https:") return;
  // Our own files → network-first (fresh code wins online). The heavy, immutable
  // CDN assets (Pyodide/numpy) → cache-first (fast, and offline-capable).
  if (url.origin === self.location.origin) {
    event.respondWith(networkFirst(req));
  } else {
    event.respondWith(cacheFirst(req));
  }
});

// NETWORK-FIRST: prefer the freshly-served file, refreshing the cache as we go;
// fall back to cache only when the network is unavailable (offline).
async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(req);
    if (res && res.ok) {
      // Clone before returning: a Response body can only be read once.
      cache.put(req, res.clone()).catch(() => {});
    }
    return res;
  } catch (err) {
    // Offline: serve the cached copy if we have one.
    const hit = await cache.match(req);
    if (hit) return hit;
    // For a navigation with nothing cached, fall back to the shell so the app
    // still boots; otherwise there's nothing we can do.
    if (req.mode === "navigate") {
      const shell = (await cache.match("index.html")) || (await cache.match("./"));
      if (shell) return shell;
    }
    throw err;
  }
}

// CACHE-FIRST: serve from cache if present (fast); otherwise fetch and stash.
// Used only for cross-origin, URL-versioned CDN assets that never change.
async function cacheFirst(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  // Cache real (ok) and opaque (no-CORS cross-origin) responses. jsDelivr serves
  // CORS, so Pyodide/numpy come back as real, fully-replayable responses.
  if (res && (res.ok || res.type === "opaque")) {
    cache.put(req, res.clone()).catch(() => {});
  }
  return res;
}
