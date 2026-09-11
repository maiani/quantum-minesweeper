# qminesweeper/server.py
from __future__ import annotations

import csv
import io
import json
import logging
import re
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from qminesweeper import __version__
from qminesweeper.auth import enable_basic_auth
from qminesweeper.backends import make_backend as make_simulator_backend
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.database import get_store
from qminesweeper.docs_render import load_docs
from qminesweeper.engine import (
    MAX_DIM,
    MAX_ENT_LEVEL,
    MOVE_SETS,
    PROBE_REGION_LIMIT,
    WIN_CONDITIONS,
    Command,
    apply_command,
    build_game,
    parse_command,
    probe_regions,
    probe_rules_for_limit,
    probe_rules_for_regions,
    serialize_game,
    validate_setup_params,
)
from qminesweeper.game import (
    GameStatus,
    MoveSet,
    QMineSweeperGame,
    WinCondition,
)
from qminesweeper.logging_config import setup_logging
from qminesweeper.quantum_backend import QuantumGate
from qminesweeper.settings import ResetPolicy, get_settings

# --------- Logging ---------
logger = setup_logging()

# --------- Settings ---------
settings = get_settings()

# --------- App & assets ---------
app = FastAPI()

# Paths reachable without the site password. /analytics is here because a
# browser-only client has no credentials to present, so the ingest route cannot
# sit behind Basic Auth; it is disabled by default and validates everything it
# accepts. Named so tests can assert against the real list.
# /app/* is the installable PWA. It is exempt because a service worker cannot
# answer a Basic Auth challenge cleanly: an installed app would fail its update
# fetches in confusing ways. The password still guards the server-run game and
# the admin pages.
# "/app" itself is listed alongside the prefix so the mount's redirect to
# "/app/" is reached; without it, typing the bare path gets a password prompt.
AUTH_EXEMPT_PATHS = [
    "/health", "/robots.txt", "/sitemap.xml", "/static/*", "/analytics", "/app/config", "/app", "/app/*"
]

enable_basic_auth(
    app,
    username=settings.USER,
    password=settings.PASS,
    exclude_paths=AUTH_EXEMPT_PATHS,
)

# Browser-only sessions may be served from another origin (the static build can
# be hosted anywhere), so the ingest route needs CORS. Scoped to the configured
# origins and to POST; nothing else on the site becomes cross-origin readable.
_analytics_origins = [o.strip() for o in settings.ANALYTICS_ALLOWED_ORIGINS.split(",") if o.strip()]
if settings.ENABLE_BROWSER_ANALYTICS and _analytics_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_analytics_origins,
        allow_methods=["POST"],
        allow_headers=["content-type"],
    )

# --------- Abusive-bot blocklist ---------
BLOCKED_BOT_AGENTS = (
    "tiktokspider",
    "bytespider",
    "mj12bot",
    "ahrefsbot",
    "semrushbot",
    "dotbot",
    "petalbot",
    "dataforseobot",
    "blexbot",
    "mauibot",
    "serpstatbot",
    "seekportbot",
)


@app.middleware("http")
async def gate_browser_app(request: Request, call_next):
    """Hide /app when the deployment has switched the installable app off.

    The mount is created at startup, but QMS_ENABLE_BROWSER_APP is a live
    setting the admin dashboard can change, so the check belongs per request.
    404 rather than 403: a deployment that does not offer the app should not
    advertise that it exists.
    """
    path = request.url.path
    if (path == "/app" or path.startswith("/app/")) and not settings.ENABLE_BROWSER_APP:
        return PlainTextResponse("Not found", status_code=404)
    return await call_next(request)


@app.middleware("http")
async def block_abusive_bots(request: Request, call_next):
    ua = request.headers.get("user-agent", "").lower()
    if ua and any(bot in ua for bot in BLOCKED_BOT_AGENTS):
        return PlainTextResponse("Forbidden", status_code=403)
    return await call_next(request)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("qminesweeper.web")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DOCS_DIR = BASE_DIR / "docs"

STATS_DB = get_store()
# Environment variables provide deployment defaults. Values saved through the
# admin dashboard deliberately override only its allowlisted product settings,
# and live in the same durable SQLite volume as game statistics.
try:
    settings.apply_admin_values(STATS_DB.load_app_settings())
except ValueError as exc:
    log.error(f"Ignoring invalid persisted application settings: {exc}")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["now"] = datetime.now
templates.env.globals["version"] = __version__
templates.env.globals["BASE_URL"] = settings.BASE_URL
templates.env.globals["GA_MEASUREMENT_ID"] = settings.GA_MEASUREMENT_ID

# --------- Installable PWA (optional) ---------
# A deployment can hand out the browser-only build so visitors install it and
# keep playing offline. This does not change how the site plays: the
# server-rendered game still runs here. It adds a second way to play that runs
# entirely in the visitor's browser.
#
# Serving it from this origin is what makes analytics simple: same-origin needs
# no CORS, and the bundle can point at the relative "/analytics", so one image
# works on any host. QMS_ENABLE_BROWSER_APP decides whether to offer it;
# QMS_BROWSER_DIST_DIR says where the bundle is, and the Docker image sets it.
BROWSER_DIST_DIR = Path(settings.BROWSER_DIST_DIR).expanduser() if settings.BROWSER_DIST_DIR else None
BROWSER_APP_AVAILABLE = bool(BROWSER_DIST_DIR and (BROWSER_DIST_DIR / "index.html").is_file())
if settings.BROWSER_DIST_DIR and not BROWSER_APP_AVAILABLE:
    log.warning(f"QMS_BROWSER_DIST_DIR={settings.BROWSER_DIST_DIR} has no index.html; /app is not served")

FEATURES = settings.product_config().template_features(browser_app_available=BROWSER_APP_AVAILABLE)
templates.env.globals["FEATURES"] = FEATURES


# The header renders the active-game count on every server page. Cache it briefly
# so a burst of requests doesn't hit the DB on each render (single-instance app).
_ONLINE_TTL_SECONDS = 10.0
_online_cache = {"at": 0.0, "value": 0}


def _online_count() -> int:
    now = time.monotonic()
    if now - _online_cache["at"] > _ONLINE_TTL_SECONDS:
        _online_cache["value"] = STATS_DB.online_active()
        _online_cache["at"] = now
    return _online_cache["value"]


templates.env.globals["online_count"] = _online_count


DOCS = load_docs(DOCS_DIR)
templates.env.globals["docs"] = DOCS


@app.get("/app/config")
def browser_app_config():
    """Runtime product choices for the installable browser app.

    This route is intentionally public: an installed app cannot present Basic
    Auth credentials, and these are visible product switches rather than
    sensitive settings. The app uses its bundled choices offline and refreshes
    this value before starting a new game when it is served from this origin.
    """
    product = settings.product_config()
    return JSONResponse({"product": product.browser_product(), "config": product.game_config()})


class RevalidatingStaticFiles(StaticFiles):
    """StaticFiles that asks the browser to revalidate instead of guessing.

    Starlette sends `etag` and `last-modified` but no `Cache-Control`. With no
    explicit freshness a browser invents one -- roughly a tenth of the file's
    age -- so a bundle that has been live for a couple of months is treated as
    fresh for days, and a newly deployed one is not fetched at all. That is not
    a theoretical risk for the PWA: its service worker is network-first, but its
    `fetch()` reads through the same HTTP cache, so a heuristically fresh entry
    defeats the whole update path and the installed app stays on the old build
    until the invented window expires.

    `no-cache` does not mean "do not store" -- it means "store, but revalidate
    before reusing". Paired with the etag Starlette already sends, an unchanged
    file costs one conditional request answered with an empty 304, and offline
    play is unaffected because that is served from the service worker's Cache
    Storage, not from here.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/static", RevalidatingStaticFiles(directory=str(STATIC_DIR)), name="static")

# Mounted whenever a bundle exists; QMS_ENABLE_BROWSER_APP is enforced per
# request below, so the admin dashboard can turn it off without a restart.
# html=True serves index.html for the directory itself, and the bundle's paths
# are all relative, so it works unchanged under this prefix. Its service worker
# sits at /app/sw.js and therefore scopes to /app/, leaving the routes at /
# untouched.
if BROWSER_APP_AVAILABLE:
    app.mount(
        "/app",
        RevalidatingStaticFiles(directory=str(BROWSER_DIST_DIR), html=True),
        name="browser_app",
    )
    log.info(f"Serving the installable browser app from {BROWSER_DIST_DIR} at /app/")

# --------- Long-lived (optional) user cookie ONLY ---------
USER_COOKIE = "qmsuser"


def ensure_user_id(request: Request) -> str:
    uid = request.cookies.get(USER_COOKIE)
    if not uid:
        uid = str(uuid4())
        log.info(f"New user_id created: {uid}")
    return uid


def attach_user_cookie(resp: Response, user_id: str, request: Request) -> Response:
    resp.set_cookie(
        key=USER_COOKIE,
        value=user_id,
        path="/",
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https"),
    )
    return resp


# --------- Admin session (signed cookie) ---------
# Admin is gated by a short-lived signed cookie issued on a POST login, rather
# than a password echoed through URL query strings (which leak into access logs,
# proxies, browser history and Referer headers). The signing secret is derived
# from ADMIN_PASS, so a cookie cannot be forged without knowing the password.
ADMIN_COOKIE = "qms_admin"
ADMIN_SESSION_MAX_AGE = 8 * 3600  # seconds


def _admin_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.ADMIN_PASS or "", salt="qms-admin-session")


def admin_enabled() -> bool:
    return bool(settings.ADMIN_PASS)


def admin_authed(request: Request) -> bool:
    """True if the request carries a valid, unexpired admin session cookie."""
    if not admin_enabled():
        return False
    token = request.cookies.get(ADMIN_COOKIE)
    if not token:
        return False
    try:
        _admin_serializer().loads(token, max_age=ADMIN_SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


# --------- In-memory game store ---------
# game_id -> {board, game, config}
GAMES: dict[str, dict] = {}


# --------- Helpers ---------
def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _record_outcome(game_id: str, game: QMineSweeperGame, user_id: str) -> None:
    """Persist a terminal WIN/LOST to analytics (idempotent UPDATE).

    Called from both /move (moves no longer reload, so the move that ends the
    game is where the outcome is observed) and /game (a later refresh).
    """
    if game.status == GameStatus.WIN:
        log.info(f"WIN user={user_id} gid={game_id}")
        STATS_DB.outcome(game_id=game_id, ts=_now_iso(), status="WIN")
    elif game.status == GameStatus.LOST:
        log.info(f"LOST user={user_id} gid={game_id}")
        STATS_DB.outcome(game_id=game_id, ts=_now_iso(), status="LOST")


def _probe_region_limit() -> int:
    """Regions this deployment allows: all of them, or none when switched off."""
    return PROBE_REGION_LIMIT if settings.ENABLE_ENTANGLEMENT_PROBES else 0


def build_board_and_game(
    rows: int,
    cols: int,
    mines: int,
    ent_level: int,
    win: WinCondition,
    moves: MoveSet,
    entanglement_probes: bool = True,
    two_area_probes: bool = False,
):
    # A deployment with the probe switched off gets no probe rules, whatever the
    # setup asked for. Applied on every build, so a new-same game follows a flag
    # change too.
    entanglement_probes, two_area_probes = probe_rules_for_limit(
        entanglement_probes, two_area_probes, _probe_region_limit()
    )
    # Construction (and validation) is shared with the browser session via engine.build_game.
    return build_game(
        make_simulator_backend(settings.BACKEND),
        rows,
        cols,
        mines,
        ent_level,
        win,
        moves,
        entanglement_probes,
        two_area_probes,
    )


def prune_stale_games() -> None:
    """
    Prune games that have been inactive longer than the abandonment threshold.

    - In-memory GAMES dict: remove stale entries, mark DB outcome if still ongoing.
    - Database: call prune_abandoned() to mark old rows as ABANDONED.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ABANDON_THRESHOLD_MIN)

    # Clean in-memory store
    stale_ids = [gid for gid, rec in GAMES.items() if rec.get("last_seen") and rec["last_seen"] < cutoff]
    for gid in stale_ids:
        game = GAMES[gid]["game"]
        if game.status == GameStatus.ONGOING:
            STATS_DB.outcome(game_id=gid, ts=_now_iso(), status="ABANDONED")
        GAMES.pop(gid, None)

    # Clean database store
    n = STATS_DB.prune_abandoned(minutes=settings.ABANDON_THRESHOLD_MIN)
    if n:
        log.info(f"Pruned {n} abandoned games (scheduled)")


# --------- Routes ---------
def _absolute_site_url(path: str) -> str:
    """Build an absolute public URL for crawler-facing metadata."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{settings.BASE_URL.rstrip('/')}{normalized_path}"


@app.get("/health")
def health():
    return PlainTextResponse("ok")


# --------- Browser analytics ingest ---------
# A browser-only session runs entirely in the player's browser, so nothing
# records the games it plays. This endpoint lets such a session report the same
# rows the server writes for itself, when it has connectivity and the
# deployment has opted in.
#
# Everything arriving here is client-asserted and unauthenticated, so the
# payload is validated strictly and stored with source='browser'. Board limits
# come from engine.validate_setup_params and the vocabularies from
# WIN_CONDITIONS / MOVE_SETS, so this route cannot drift from the real rules.
ANALYTICS_MAX_BODY_BYTES = 256 * 1024
ANALYTICS_MAX_GAMES = 50
ANALYTICS_MAX_GATES = 4096
ANALYTICS_MAX_COUNTER = 1_000_000
ANALYTICS_STATUSES = {"ONGOING", "WIN", "LOST", "ABANDONED"}
ANALYTICS_FUTURE_SKEW = timedelta(minutes=5)
_ANALYTICS_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# Gate names come from QuantumGate so the route accepts exactly the vocabulary
# the simulators implement, and gains new gates automatically.
_ANALYTICS_GATE_NAMES = {gate.value for gate in QuantumGate}
_analytics_rate_lock = threading.Lock()
_analytics_global_requests: deque[float] = deque()
_analytics_client_requests: dict[str, deque[float]] = {}


def _analytics_client_key(request: Request) -> str:
    """Best-effort rate-limit key; the global limit remains spoof-proof."""
    headers = getattr(request, "headers", {})
    forwarded = headers.get("x-forwarded-for", "") if headers else ""
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:128]
    client = getattr(request, "client", None)
    return str(getattr(client, "host", "unknown"))[:128]


def _analytics_rate_allowed(request: Request) -> bool:
    """Apply a small in-process sliding-window guard to the public endpoint."""
    now = time.monotonic()
    cutoff = now - 60.0
    key = _analytics_client_key(request)
    with _analytics_rate_lock:
        while _analytics_global_requests and _analytics_global_requests[0] <= cutoff:
            _analytics_global_requests.popleft()
        # A spoofed forwarding header can create many keys over time. Keep the
        # map bounded by discarding inactive buckets before admitting new ones;
        # the independent global request window is the hard abuse ceiling.
        too_many_client_buckets = (
            key not in _analytics_client_requests
            and len(_analytics_client_requests) >= settings.ANALYTICS_GLOBAL_LIMIT_PER_MINUTE
        )
        if too_many_client_buckets:
            for stale_key, requests in list(_analytics_client_requests.items()):
                while requests and requests[0] <= cutoff:
                    requests.popleft()
                if not requests:
                    del _analytics_client_requests[stale_key]
        client_requests = _analytics_client_requests.setdefault(key, deque())
        while client_requests and client_requests[0] <= cutoff:
            client_requests.popleft()
        if (
            len(_analytics_global_requests) >= settings.ANALYTICS_GLOBAL_LIMIT_PER_MINUTE
            or len(client_requests) >= settings.ANALYTICS_RATE_LIMIT_PER_MINUTE
        ):
            return False
        _analytics_global_requests.append(now)
        client_requests.append(now)
        return True


def _analytics_int(raw: Any, field: str, *, low: int, high: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{field} must be an integer")
    if not (low <= raw <= high):
        raise ValueError(f"{field} must be between {low} and {high}")
    return raw


def _analytics_timestamp(raw: Any, field: str, *, required: bool = True) -> Optional[datetime]:
    """Accept only a parseable ISO-8601 timestamp, returned normalized."""
    if raw is None or raw == "":
        if required:
            raise ValueError(f"{field} is required")
        return None
    if not isinstance(raw, str) or len(raw) > 40:
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _analytics_circuit(raw: Any, n_cells: int) -> list[list[Any]]:
    """Validate a preparation circuit against the real gate vocabulary."""
    if not isinstance(raw, list):
        raise ValueError("prep_circuit must be a list")
    if len(raw) > ANALYTICS_MAX_GATES:
        raise ValueError(f"prep_circuit may hold at most {ANALYTICS_MAX_GATES} gates")
    out: list[list[Any]] = []
    for entry in raw:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("each prep_circuit entry must be [gate, targets]")
        gate, targets = entry
        if gate not in _ANALYTICS_GATE_NAMES:
            raise ValueError(f"unknown gate {gate!r} in prep_circuit")
        if not isinstance(targets, list) or not targets:
            raise ValueError("prep_circuit targets must be a non-empty list")
        checked = [_analytics_int(t, "prep_circuit target", low=0, high=n_cells - 1) for t in targets]
        out.append([str(gate), checked])
    return out


def _validate_analytics_game(raw: Any) -> Dict[str, Any]:
    """Return one normalized game row, or raise ValueError describing the fault."""
    if not isinstance(raw, dict):
        raise ValueError("each game must be an object")

    game_id = raw.get("game_id")
    if not isinstance(game_id, str) or not _ANALYTICS_ID_RE.match(game_id):
        raise ValueError("game_id must be 1-64 characters of [A-Za-z0-9_-]")
    user_id = raw.get("user_id") or ""
    if not isinstance(user_id, str) or (user_id and not _ANALYTICS_ID_RE.match(user_id)):
        raise ValueError("user_id must be 1-64 characters of [A-Za-z0-9_-]")

    rows = _analytics_int(raw.get("rows"), "rows", low=1, high=MAX_DIM)
    cols = _analytics_int(raw.get("cols"), "cols", low=1, high=MAX_DIM)
    mines = _analytics_int(raw.get("mines"), "mines", low=0, high=rows * cols)
    ent_level = _analytics_int(raw.get("ent_level"), "ent_level", low=0, high=MAX_ENT_LEVEL)
    # Reuse the real setup validation so this route cannot accept a board the
    # game itself would reject.
    validate_setup_params(rows, cols, mines, ent_level)

    win_cond = raw.get("win_cond")
    if win_cond not in WIN_CONDITIONS:
        raise ValueError(f"win_cond must be one of {sorted(WIN_CONDITIONS)}")
    moveset = raw.get("moveset")
    if moveset not in MOVE_SETS:
        raise ValueError(f"moveset must be one of {sorted(MOVE_SETS)}")

    status = raw.get("status")
    if status is not None and status not in ANALYTICS_STATUSES:
        raise ValueError(f"status must be one of {sorted(ANALYTICS_STATUSES)}")

    created_at = _analytics_timestamp(raw.get("created_at"), "created_at")
    last_seen = _analytics_timestamp(raw.get("last_seen"), "last_seen")
    ended_at = _analytics_timestamp(raw.get("ended_at"), "ended_at", required=False)
    assert created_at is not None and last_seen is not None
    if created_at > last_seen:
        raise ValueError("created_at must not be after last_seen")
    if last_seen > datetime.now(timezone.utc) + ANALYTICS_FUTURE_SKEW:
        raise ValueError("last_seen is too far in the future")
    if ended_at is not None and not (created_at <= ended_at <= last_seen):
        raise ValueError("ended_at must be between created_at and last_seen")
    if status == "ONGOING" and ended_at is not None:
        raise ValueError("ONGOING games must not have ended_at")
    if status in {"WIN", "LOST", "ABANDONED"} and ended_at is None:
        raise ValueError("finished games require ended_at")

    return {
        "game_id": game_id,
        "user_id": user_id,
        "created_at": created_at.isoformat(),
        "last_seen": last_seen.isoformat(),
        "ended_at": ended_at.isoformat() if ended_at is not None else None,
        "rows": rows,
        "cols": cols,
        "mines": mines,
        "ent_level": ent_level,
        "win_cond": win_cond,
        "moveset": moveset,
        "status": status,
        "prep_circuit": _analytics_circuit(raw.get("prep_circuit") or [], rows * cols),
        "resets": _analytics_int(raw.get("resets", 0), "resets", low=0, high=ANALYTICS_MAX_COUNTER),
        "moves_measures": _analytics_int(
            raw.get("moves_measures", 0), "moves_measures", low=0, high=ANALYTICS_MAX_COUNTER
        ),
        "moves_gates": _analytics_int(raw.get("moves_gates", 0), "moves_gates", low=0, high=ANALYTICS_MAX_COUNTER),
    }


@app.post("/analytics")
async def analytics_ingest(request: Request):
    """Accept a batch of browser-reported games.

    Reports are idempotent, so a client that was offline can safely resend, and
    a partly-valid batch stores what it can rather than failing whole: a client
    cannot fix a rejected row, and dropping the good ones with it would lose
    data for no gain. The response reports both counts so a client can drop what
    was accepted from its queue.
    """
    if not settings.ENABLE_BROWSER_ANALYTICS:
        # 404 rather than 403: a deployment that has not opted in should not
        # advertise that the route exists.
        return JSONResponse({"detail": "Not found"}, status_code=404)

    if not _analytics_rate_allowed(request):
        return JSONResponse(
            {"detail": "Too many analytics requests"},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    body = await request.body()
    if len(body) > ANALYTICS_MAX_BODY_BYTES:
        return JSONResponse({"detail": "Payload too large"}, status_code=413)
    try:
        payload = json.loads(body or b"{}")
    except ValueError:
        return JSONResponse({"detail": "Body must be JSON"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"detail": "Body must be a JSON object"}, status_code=400)

    games = payload.get("games")
    if not isinstance(games, list):
        return JSONResponse({"detail": "games must be a list"}, status_code=400)
    if len(games) > ANALYTICS_MAX_GAMES:
        return JSONResponse({"detail": f"At most {ANALYTICS_MAX_GAMES} games per batch"}, status_code=413)

    accepted, rejected = [], []
    for entry in games:
        try:
            row = _validate_analytics_game(entry)
        except ValueError as exc:
            rejected.append(str(exc))
            continue
        if STATS_DB.ingest_game(row):
            accepted.append(row["game_id"])
        else:
            rejected.append(f"{row['game_id']}: refused")

    if rejected:
        log.info(f"Analytics batch: {len(accepted)} accepted, {len(rejected)} rejected ({rejected[:3]})")
    pruned = STATS_DB.prune_browser_analytics(
        max_rows=settings.ANALYTICS_MAX_BROWSER_ROWS,
        retention_days=settings.ANALYTICS_RETENTION_DAYS,
    )
    if pruned:
        log.info(f"Pruned {pruned} expired or excess browser analytics rows")
    # The active-game count rides along so the browser app can show the same
    # counter the server pages do, without a second endpoint or a polling timer.
    # It is the cached value, so this costs no extra query. Carrying it here also
    # makes the counter honest by construction: a client only learns the number
    # while it is itself reporting, so the count always includes players like it.
    return JSONResponse({"accepted": accepted, "rejected": len(rejected), "online": _online_count()})


@app.get("/robots.txt")
def robots_txt():
    body = templates.env.get_template("robots.txt").render(
        disallow_paths=[
            "/move",
            # Crawl trap: every game mints a unique game_id, so these query URLs are
            # infinite. Keep the canonical /setup and /about indexable, but tell
            # well-behaved bots not to enumerate the game_id variants.
            "/*?game_id=",
            "/admin/db_download",
            "/admin/update_settings",
            "/admin/logout",
        ],
        sitemap_url=_absolute_site_url("/sitemap.xml"),
    )
    return PlainTextResponse(body)


@app.get("/sitemap.xml")
def sitemap_xml():
    paths = ["/setup"]
    if settings.ENABLE_ABOUT:
        paths.append("/about")

    body = templates.env.get_template("sitemap.xml").render(
        urls=[_absolute_site_url(path) for path in paths],
    )
    return Response(content=body, media_type="application/xml")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    prune_stale_games()

    # Stateless: expose setup at a stable URL instead of minting crawlable
    # session IDs before a game exists.
    user_id = ensure_user_id(request)

    # A deployment that offers the installable app makes it the landing, so play
    # happens in the visitor's browser rather than on this server. The
    # server-rendered game stays reachable at /setup, which is also what the
    # sitemap points crawlers at, since /app/ is a client-rendered shell.
    #
    # RedirectResponse is a 307, deliberately: the target depends on a setting
    # the admin dashboard can change, and a permanent redirect would be cached
    # by browsers and keep sending visitors to /app/ after it was switched off.
    offer_app = settings.ENABLE_BROWSER_APP and BROWSER_APP_AVAILABLE
    resp = RedirectResponse("/app/" if offer_app else "/setup")
    return attach_user_cookie(resp, user_id, request)


@app.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request, game_id: Optional[str] = Query(None)):
    prune_stale_games()

    user_id = ensure_user_id(request)
    log.info(f"User {user_id} -> setup")
    resp = templates.TemplateResponse(
        request,
        "setup.html",
        {
            "game_id": game_id,
            "error": None,
        },
    )
    return attach_user_cookie(resp, user_id, request)


def _render_setup_error(request: Request, user_id: str, game_id: str, error: str) -> Response:
    resp = templates.TemplateResponse(
        request,
        "setup.html",
        {"game_id": game_id, "error": error},
        status_code=400,
    )
    return attach_user_cookie(resp, user_id, request)


@app.post("/setup")
async def setup_post(
    request: Request,
    rows: int = Form(...),
    cols: int = Form(...),
    mines: int = Form(...),
    ent_level: int = Form(...),
    win_condition: str = Form(...),
    move_set: str = Form(...),
    entanglement_probe_regions: int = Form(0),
    game_id: Optional[str] = Query(None, alias="game_id"),
):
    user_id = ensure_user_id(request)
    # Always generate a fresh game_id for a new game
    game_id = str(uuid4())

    win = WIN_CONDITIONS.get(win_condition.lower(), WinCondition.IDENTIFY)
    mv = MOVE_SETS.get(move_set.lower(), MoveSet.CLASSIC)
    # Setup chooses a region count; the game keeps it as its two rule flags.
    entanglement_probes, two_area_probes = probe_rules_for_regions(entanglement_probe_regions, _probe_region_limit())

    try:
        board, game = build_board_and_game(rows, cols, mines, ent_level, win, mv, entanglement_probes, two_area_probes)
    except ValueError as e:
        log.info(f"SETUP rejected user={user_id} rows={rows} cols={cols} mines={mines} ent={ent_level}: {e}")
        return _render_setup_error(request, user_id, game_id, str(e))
    GAMES[game_id] = {
        "board": board,
        "game": game,
        "config": {
            "rows": rows,
            "cols": cols,
            "mines": mines,
            "ent_level": ent_level,
            "win": win,
            "moves": mv,
            "entanglement_probes": entanglement_probes,
            "two_area_probes": two_area_probes,
        },
        "last_seen": datetime.now(timezone.utc),
    }

    # Persist creation + initial heartbeat
    ts = _now_iso()
    STATS_DB.game_created(
        game_id=game_id,
        user_id=user_id,
        ts=ts,
        rows=rows,
        cols=cols,
        mines=mines,
        ent_level=ent_level,
        win_cond=win.name,
        moveset=mv.name,
        prep_circuit=board.preparation_circuit,
    )
    STATS_DB.heartbeat(game_id=game_id, ts=ts)

    log.info(
        f"SETUP user={user_id} gid={game_id} rows={rows} cols={cols} mines={mines} "
        f"ent={ent_level} win={win.name} moves={mv.name}"
    )

    return attach_user_cookie(RedirectResponse(f"/game?game_id={game_id}", status_code=303), user_id, request)


@app.get("/game", response_class=HTMLResponse)
async def game_get(request: Request, game_id: Optional[str] = Query(None, alias="game_id")):
    user_id = ensure_user_id(request)
    if not game_id or game_id not in GAMES:
        return attach_user_cookie(RedirectResponse("/setup", status_code=303), user_id, request)

    # Update last_seen + DB heartbeat (online)
    GAMES[game_id]["last_seen"] = datetime.now(timezone.utc)
    STATS_DB.heartbeat(game_id=game_id, ts=_now_iso())

    board: QMineSweeperBoard = GAMES[game_id]["board"]
    game: QMineSweeperGame = GAMES[game_id]["game"]

    # Persist terminal outcome once it happens
    _record_outcome(game_id, game, user_id)

    # Game state (the shared contract) + app config (server-only feature flags),
    # inlined separately into the shell. render.js builds the view from both.
    state = serialize_game(board, game, game_id)
    config = settings.product_config().game_config(
        entanglement_probes=game.cfg.entanglement_probes,
        two_area_probes=game.cfg.two_area_probes,
    )
    return attach_user_cookie(
        templates.TemplateResponse(
            request,
            "game.html",
            {"state": state, "config": config, "ABOUT_HREF": "/about"},
        ),
        user_id,
        request,
    )


@app.post("/move")
async def move_post(
    request: Request,
    cmd: str = Form(...),
    game_id: Optional[str] = Query(None, alias="game_id"),
):
    """
    Apply one move command and return the new game state as JSON.

    The frontend (render.js via the JS Engine) fetches this and re-renders in
    place — no page reload. `cmd` is a move string ("M 2,3", "X 1,1", "P 4,4");
    parsing/dispatch goes through the shared engine (parse_command/apply_command).
    """
    user_id = ensure_user_id(request)
    if not game_id or game_id not in GAMES:
        # Game expired/pruned: tell the client to fall back to setup.
        return JSONResponse({"error": "game_not_found", "redirect": "/setup"}, status_code=404)

    board: QMineSweeperBoard = GAMES[game_id]["board"]
    game: QMineSweeperGame = GAMES[game_id]["game"]

    try:
        command = parse_command(cmd)
        apply_command(board, game, command)
        if command.kind == "measure":
            STATS_DB.increment_move(game_id=game_id, kind="measure")
        elif command.kind == "gate":
            STATS_DB.increment_move(game_id=game_id, kind="gate")
        # pin is not counted
    except Exception as e:
        # Invalid/illegal command: log and return the unchanged state so the UI
        # stays consistent (the move is simply a no-op).
        log.exception(f"MOVE error gid={game_id} cmd='{cmd}' err={e}")

    _record_outcome(game_id, game, user_id)
    GAMES[game_id]["last_seen"] = datetime.now(timezone.utc)
    STATS_DB.heartbeat(game_id=game_id, ts=_now_iso())

    return serialize_game(board, game, game_id)


@app.post("/probe")
async def probe_post(request: Request, game_id: Optional[str] = Query(None, alias="game_id")):
    """Read an advanced region entropy diagnostic for a live game."""
    if not game_id or game_id not in GAMES:
        return JSONResponse({"error": "game_not_found", "redirect": "/setup"}, status_code=404)
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        result = probe_regions(
            GAMES[game_id]["board"],
            GAMES[game_id]["game"],
            payload.get("area_a"),
            payload.get("area_b"),
        )
    except (ValueError, TypeError, KeyError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse(result)


@app.post("/game")
async def game_post(
    request: Request,
    action: str = Form(...),
    game_id: Optional[str] = Query(None, alias="game_id"),
):
    if not game_id or game_id not in GAMES:
        return RedirectResponse("/setup", status_code=303)

    board: QMineSweeperBoard = GAMES[game_id]["board"]
    game: QMineSweeperGame = GAMES[game_id]["game"]
    cfg = GAMES[game_id]["config"]

    if action == "reset":
        allowed = False
        if settings.RESET_POLICY == "any":
            allowed = True
        elif settings.RESET_POLICY == "sandbox" and game.cfg.win_condition == WinCondition.SANDBOX:
            allowed = True

        if allowed:
            apply_command(board, game, Command("reset"))
            GAMES[game_id]["last_seen"] = datetime.now(timezone.utc)
            STATS_DB.reset_move_counters(game_id=game_id, ts=_now_iso())
        else:
            log.info(f"Reset not allowed by policy ({settings.RESET_POLICY}) for gid={game_id}")

    elif action == "new_same":
        # Fresh game_id, same rules
        new_game_id = str(uuid4())
        board2, game2 = build_board_and_game(
            cfg["rows"],
            cfg["cols"],
            cfg["mines"],
            cfg["ent_level"],
            cfg["win"],
            cfg["moves"],
            cfg.get("entanglement_probes", True),
            cfg.get("two_area_probes", False),
        )
        GAMES[new_game_id] = {
            "board": board2,
            "game": game2,
            "config": cfg.copy(),
            "last_seen": datetime.now(timezone.utc),
        }
        ts = _now_iso()
        STATS_DB.game_created(
            game_id=new_game_id,
            user_id=ensure_user_id(request),
            ts=ts,
            rows=cfg["rows"],
            cols=cfg["cols"],
            mines=cfg["mines"],
            ent_level=cfg["ent_level"],
            win_cond=cfg["win"].name,
            moveset=cfg["moves"].name,
            prep_circuit=board2.preparation_circuit,
        )
        STATS_DB.heartbeat(game_id=new_game_id, ts=ts)
        return RedirectResponse(f"/game?game_id={new_game_id}", status_code=303)

    elif action == "new_rules":
        # New setup flow; the next POST /setup creates the fresh game_id.
        return RedirectResponse("/setup", status_code=303)

    return RedirectResponse(f"/game?game_id={game_id}", status_code=303)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form(request: Request, error: Optional[str] = Query(None)):
    if not admin_enabled():
        return PlainTextResponse("Admin is disabled (QMS_ADMIN_PASS is not set).", status_code=404)
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {"error": error},
    )


@app.post("/admin/login")
def admin_login(request: Request, admin_pass: str = Form(...)):
    if not admin_enabled():
        return PlainTextResponse("Admin is disabled (QMS_ADMIN_PASS is not set).", status_code=404)
    if not secrets.compare_digest(admin_pass, settings.ADMIN_PASS or ""):
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {"error": "Incorrect password."},
            status_code=403,
        )
    resp = RedirectResponse("/admin", status_code=303)
    resp.set_cookie(
        key=ADMIN_COOKIE,
        value=_admin_serializer().dumps("ok"),
        path="/admin",
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https"),
        max_age=ADMIN_SESSION_MAX_AGE,
    )
    return resp


@app.post("/admin/logout")
def admin_logout(request: Request):
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie(ADMIN_COOKIE, path="/admin")
    return resp


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request):
    if not admin_authed(request):
        return RedirectResponse("/admin/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "admin_home.html",
        {
            # Distinguishes "switched off" from "this image ships no bundle", so
            # the toggle is not silently inert.
            "browser_app_available": BROWSER_APP_AVAILABLE,
            "browser_app_enabled": settings.ENABLE_BROWSER_APP,
        },
    )


@app.post("/admin/update_settings")
async def update_settings(
    request: Request,
    ENABLE_HELP: Optional[str] = Form(None),
    ENABLE_ABOUT: Optional[str] = Form(None),
    ENABLE_TUTORIAL: Optional[str] = Form(None),
    ENABLE_SURVEY: Optional[str] = Form(None),
    ENABLE_ENTANGLEMENT_PROBES: Optional[str] = Form(None),
    ENABLE_BROWSER_APP: Optional[str] = Form(None),
    RESET_POLICY: ResetPolicy = Form("sandbox"),
):
    if not admin_authed(request):
        return RedirectResponse("/admin/login", status_code=303)

    # update settings
    settings.ENABLE_HELP = bool(ENABLE_HELP)
    settings.ENABLE_ABOUT = bool(ENABLE_ABOUT)
    settings.ENABLE_TUTORIAL = bool(ENABLE_TUTORIAL)
    settings.ENABLE_SURVEY = bool(ENABLE_SURVEY)
    settings.ENABLE_ENTANGLEMENT_PROBES = bool(ENABLE_ENTANGLEMENT_PROBES)
    settings.ENABLE_BROWSER_APP = bool(ENABLE_BROWSER_APP)
    settings.RESET_POLICY = RESET_POLICY

    # update template globals
    templates.env.globals["FEATURES"].clear()
    templates.env.globals["FEATURES"].update(
        settings.product_config().template_features(browser_app_available=BROWSER_APP_AVAILABLE)
    )

    if not STATS_DB.save_app_settings(settings.admin_values()):
        return PlainTextResponse("Could not persist settings", status_code=500)

    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/db_view", response_class=HTMLResponse)
def view_db(request: Request):
    if not admin_authed(request):
        return RedirectResponse("/admin/login", status_code=303)

    rows = STATS_DB.recent_games(limit=100)

    # copy each row before formatting datetimes, so the store's output is not mutated
    formatted_rows = []
    for r in rows:
        d = dict(r)
        for k, v in d.items():
            if isinstance(v, str) and (k.endswith("_at") or k.endswith("_time") or k == "last_seen"):
                try:
                    dt = datetime.fromisoformat(v)
                    d[k] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
        formatted_rows.append(d)

    return templates.TemplateResponse(
        request,
        "db_view.html",
        {"rows": formatted_rows, "columns": STATS_DB.game_columns()},
    )


@app.get("/admin/db_download")
def download_db(request: Request):
    if not admin_authed(request):
        return RedirectResponse("/admin/login", status_code=303)

    # Columns come from the table definition, so an export with no games still
    # has a header row instead of a leading blank line.
    columns, rows = STATS_DB.export_games()

    # write CSV into memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(rows)

    output.seek(0)
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=qms_games.csv"},
    )


@app.get("/about", response_class=HTMLResponse)
async def about_get(request: Request):
    prune_stale_games()

    user_id = ensure_user_id(request)
    log.info(f"User {user_id} opened about page")
    resp = templates.TemplateResponse(request, "about.html", {})
    return attach_user_cookie(resp, user_id, request)
