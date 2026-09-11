// =============================================================================
// analytics.js — optional game-statistics reporting for the browser-only build
// =============================================================================
//
// A browser-only session runs entirely in the page, so nothing records the
// games it plays; the server build writes an analytics row per game. This module
// lets the browser report the same rows to a server that has opted in to
// receiving them (POST /analytics).
//
// Three properties shape the design:
//
//  1. OFF UNLESS CONFIGURED. With no endpoint (window.QMS_ANALYTICS_URL unset,
//     which is the default) every entry point is a no-op and nothing is stored
//     or sent. An ordinary local or offline build therefore transmits nothing.
//  2. OFFLINE-FIRST. The app is installable and expected to run without a
//     network, so reports queue in localStorage and flush when connectivity
//     returns. Losing the queue is acceptable; blocking the game is not.
//  3. IDEMPOTENT. The queue is keyed by game_id, so a game reported while
//     ongoing is replaced by its later state rather than duplicated, and the
//     server upserts, so a client that resends after a failed flush is safe.
//
// Nothing here ever throws into the caller: analytics must not be able to break
// gameplay, so every operation is wrapped and failures are at most a console
// warning.

const QMS_ANALYTICS_KEY = "qms.analytics.queue.v1";
// Matches the server's per-batch cap (ANALYTICS_MAX_GAMES in server.py). Older
// entries are dropped first if the queue somehow grows past it while offline.
const QMS_ANALYTICS_MAX_QUEUE = 50;

const QMSAnalytics = {
  url: null,
  _flushing: false,

  // Called once at startup with the endpoint the build was configured with.
  // Absent or empty leaves analytics disabled for the life of the page.
  configure(url) {
    this.url = typeof url === "string" && url.trim() ? url.trim() : null;
    if (!this.url) return;
    // Flush anything left over from a previous visit, then whenever the browser
    // regains connectivity.
    window.addEventListener("online", () => this.flush());
    // A player closing the tab is the common way a finished game would be lost,
    // so make a best-effort send while the page is still alive. visibilitychange
    // is used rather than unload because mobile browsers may never fire unload.
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") this._sendBeacon();
    });
    this.flush();
  },

  get enabled() {
    return Boolean(this.url);
  },

  // --- queue persistence -----------------------------------------------------
  // localStorage can throw (private browsing, storage disabled), and a corrupt
  // value must not wedge the page, so both directions fail soft to an empty
  // queue rather than propagating.
  _read() {
    try {
      const raw = localStorage.getItem(QMS_ANALYTICS_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  },

  _write(queue) {
    try {
      localStorage.setItem(QMS_ANALYTICS_KEY, JSON.stringify(queue));
    } catch (err) {
      // Full or unavailable storage: drop the queue rather than fail the move.
      console.warn("analytics queue could not be saved", err);
    }
  },

  // --- public API ------------------------------------------------------------

  // Queue one game record (the dict BrowserSession.analytics_record produces),
  // replacing any earlier report of the same game, then try to send.
  record(row) {
    if (!this.enabled || !row || !row.game_id) return;
    const queue = this._read().filter((entry) => entry.game_id !== row.game_id);
    queue.push(row);
    // Keep the newest entries if the queue overflows after a long offline run.
    this._write(queue.slice(-QMS_ANALYTICS_MAX_QUEUE));
    this.flush();
  },

  // POST the queue and decide, from the status alone, whether to keep it.
  //
  // Retry policy, which matters because a wrong choice either loses data or
  // resends forever:
  //   - network error, 429, or 5xx: transient, keep the queue and try again later.
  //   - 2xx: the server processed the batch. Rows it rejected as invalid are
  //     dropped with the rest, since a client cannot repair them and would
  //     otherwise resend the same bad data indefinitely.
  //   - other 4xx: this batch will never be accepted as it stands (disabled
  //     endpoint, too large), so drop it rather than loop.
  //
  // The response body is deliberately not parsed. Acceptance is already implied
  // by the status, and parsing would add a failure mode where a valid but
  // unexpected body makes the client resend data the server already stored.
  async flush() {
    if (!this.enabled || this._flushing) return;
    if (navigator.onLine === false) return;
    const queue = this._read();
    if (!queue.length) return;

    this._flushing = true;
    try {
      const res = await fetch(this.url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ games: queue }),
        // Let the request outlive a page transition where the browser allows it.
        keepalive: true,
      });
      if (res.status === 429 || res.status >= 500) return; // Keep the queue and retry later.
      this._readOnlineCount(res);
      // Drop only the exact records that were sent. Re-reading is not enough on
      // its own: a game can finish while the request is in flight, and record()
      // replaces the queued entry under the same game_id, so matching on
      // game_id alone would discard the newer result. last_seen is restamped on
      // every change, so it distinguishes them; when it matches, the two
      // records are the same report and dropping is correct either way.
      const sent = new Set(queue.map((entry) => entry.game_id + "@" + entry.last_seen));
      this._write(this._read().filter((entry) => !sent.has(entry.game_id + "@" + entry.last_seen)));
    } catch (err) {
      // Offline or blocked: the queue survives for the next attempt.
    } finally {
      this._flushing = false;
    }
  },

  // The server includes the active-game count in its reply. Read it purely as a
  // bonus and announce it as an event, leaving the DOM to the page.
  //
  // Kept strictly separate from the queue decision above, which is made from the
  // status alone: a malformed or unexpected body must never cause data the
  // server already stored to be resent. Hence the clone, so consuming the body
  // here cannot interfere, and the silent catch.
  async _readOnlineCount(res) {
    try {
      const body = await res.clone().json();
      if (typeof body.online !== "number") return;
      window.dispatchEvent(new CustomEvent("qms:online", { detail: { online: body.online } }));
    } catch (err) {
      // No usable count in this reply; the counter simply keeps its last value.
    }
  },

  // Best effort as the page goes away. sendBeacon cannot report what the server
  // accepted, so the queue is left intact; the duplicate is harmless because the
  // server upserts by game_id.
  _sendBeacon() {
    if (!this.enabled || !navigator.sendBeacon) return;
    const queue = this._read();
    if (!queue.length) return;
    try {
      const blob = new Blob([JSON.stringify({ games: queue })], { type: "application/json" });
      navigator.sendBeacon(this.url, blob);
    } catch (err) {
      // Nothing useful to do while the page is being torn down.
    }
  },
};

window.QMSAnalytics = QMSAnalytics;
