# qminesweeper/webapp.py
from __future__ import annotations

import csv
import io
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import markdown
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from markdown.extensions.toc import TocExtension

from qminesweeper import __version__
from qminesweeper.auth import enable_basic_auth
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.database import get_store
from qminesweeper.engine import Command, apply_command, parse_command, serialize_game
from qminesweeper.game import (
    GameConfig,
    GameStatus,
    MoveSet,
    QMineSweeperGame,
    WinCondition,
)
from qminesweeper.logging_config import setup_logging
from qminesweeper.settings import get_settings
from qminesweeper.stim_backend import StimBackend

# --------- Logging ---------
logger = setup_logging()

# --------- Settings ---------
settings = get_settings()

# --------- App & assets ---------
app = FastAPI()
enable_basic_auth(
    app,
    username=settings.USER,
    password=settings.PASS,
    exclude_paths=["/health", "/robots.txt", "/sitemap.xml", "/static/*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("qminesweeper.web")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DOCS_DIR = BASE_DIR / "docs"

STATS_DB = get_store()

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["now"] = datetime.now
templates.env.globals["version"] = __version__
templates.env.globals["BASE_URL"] = settings.BASE_URL

FEATURES = {
    "ENABLE_HELP": settings.ENABLE_HELP,
    "ENABLE_TUTORIAL": settings.ENABLE_TUTORIAL,
    "TUTORIAL_URL": settings.TUTORIAL_URL,
    "ENABLE_SURVEY": settings.ENABLE_SURVEY,
    "SURVEY_URL": settings.SURVEY_URL,
    "ENABLE_ABOUT": settings.ENABLE_ABOUT,
    "RESET_POLICY": settings.RESET_POLICY,
}
templates.env.globals["FEATURES"] = FEATURES
templates.env.globals["online_count"] = lambda: STATS_DB.online_active()


# --------- Markdown rendering ---------
def render_markdown(path: Path, strip_title: bool = False) -> tuple[str, str]:
    """
    Render markdown file to HTML.

    Parameters
    ----------
    path : Path
        File to read.
    strip_title : bool
        If True, extracts first heading as title and strips it from body.

    Returns
    -------
    title : str
        Title (from first heading, or filename stem if not found).
    html : str
        Rendered HTML content.
    """
    if not path.exists():
        return path.stem, "<p>Not found.</p>"

    text = path.read_text(encoding="utf-8")
    title = path.stem

    if strip_title:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                title = line.lstrip("# ").strip()
                lines = lines[i + 1 :]
                break
        text = "\n".join(lines).strip()

    html = markdown.markdown(
        text,
        extensions=[
            "fenced_code",
            "tables",
            TocExtension(),
            "pymdownx.arithmatex",
        ],
        extension_configs={"pymdownx.arithmatex": {"generic": True}},
    )
    return title, html


DOCS = {
    "simple_setup": render_markdown(DOCS_DIR / "simple_setup.md")[1],
    "advanced_setup": render_markdown(DOCS_DIR / "advanced_setup.md")[1],
    "about": render_markdown(DOCS_DIR / "about.md")[1],
}
templates.env.globals["docs"] = DOCS

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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


# Bounds for setup parameters. The UI presets stay well within these; the caps
# exist so a hostile or fat-fingered POST cannot request, e.g., a 10^5 x 10^5
# board and OOM the process before any response is sent.
MAX_DIM = 40
MAX_QUBITS = 1024
MAX_ENT_LEVEL = 10


def validate_setup_params(rows: int, cols: int, mines: int, ent_level: int) -> None:
    """Validate setup parameters, raising ValueError with a user-facing message."""
    if not (1 <= rows <= MAX_DIM) or not (1 <= cols <= MAX_DIM):
        raise ValueError(f"Board dimensions must be between 1 and {MAX_DIM} (got {rows}x{cols}).")
    if rows * cols > MAX_QUBITS:
        raise ValueError(f"Board too large: {rows}x{cols} exceeds {MAX_QUBITS} cells.")
    if not (0 <= ent_level <= MAX_ENT_LEVEL):
        raise ValueError(f"Entanglement level must be between 0 and {MAX_ENT_LEVEL} (got {ent_level}).")
    if not (0 <= mines <= rows * cols):
        raise ValueError(f"Mines must be between 0 and {rows * cols} (got {mines}).")


def make_backend():
    """Construct the simulator backend selected by settings.BACKEND.

    Stim (default) is imported at module load; the others are imported lazily so
    a browser/Pyodide build using 'purepy' never pulls in Stim or Qiskit, and the
    server never pays the Qiskit import cost unless asked for.
    """
    name = (settings.BACKEND or "stim").strip().lower()
    if name == "stim":
        return StimBackend()
    if name == "purepy":
        from qminesweeper.purepy_backend import PurePyBackend

        return PurePyBackend()
    if name == "qiskit":
        from qminesweeper.qiskit_backend import QiskitBackend

        return QiskitBackend()
    raise ValueError(f"Unknown backend {settings.BACKEND!r} (use 'stim', 'qiskit', or 'purepy')")


def build_board_and_game(rows: int, cols: int, mines: int, ent_level: int, win: WinCondition, moves: MoveSet):
    validate_setup_params(rows, cols, mines, ent_level)
    board = QMineSweeperBoard(rows, cols, backend=make_backend(), flood_fill=True)
    if ent_level == 0:
        board.span_classical_mines(mines)
    else:
        board.span_random_stabilizer_mines(mines, level=ent_level)
    board.set_clue_basis("Z")
    game = QMineSweeperGame(board, GameConfig(win_condition=win, move_set=moves))
    return board, game


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


@app.get("/robots.txt")
def robots_txt():
    body = templates.env.get_template("robots.txt").render(
        disallow_paths=[
            "/move",
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
    resp = RedirectResponse("/setup")
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
    game_id: Optional[str] = Query(None, alias="game_id"),
):
    user_id = ensure_user_id(request)
    # Always generate a fresh game_id for a new game
    game_id = str(uuid4())

    wc = {
        "clear": WinCondition.CLEAR,
        "identify": WinCondition.IDENTIFY,
        "sandbox": WinCondition.SANDBOX,
    }
    win = wc.get(win_condition.lower(), WinCondition.IDENTIFY)

    mv = {
        "classic": MoveSet.CLASSIC,
        "one": MoveSet.ONE_QUBIT,
        "one_complete": MoveSet.ONE_QUBIT_COMPLETE,
        "two": MoveSet.TWO_QUBIT,
        "two_extended": MoveSet.TWO_QUBIT_EXTENDED,
    }.get(move_set.lower(), MoveSet.CLASSIC)

    try:
        board, game = build_board_and_game(rows, cols, mines, ent_level, win, mv)
    except ValueError as e:
        log.info(f"SETUP rejected user={user_id} rows={rows} cols={cols} mines={mines} ent={ent_level}: {e}")
        return _render_setup_error(request, user_id, game_id, str(e))
    GAMES[game_id] = {
        "board": board,
        "game": game,
        "config": {"rows": rows, "cols": cols, "mines": mines, "ent_level": ent_level, "win": win, "moves": mv},
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
    if game.status == GameStatus.WIN:
        log.info(f"WIN user={user_id} gid={game_id}")
        STATS_DB.outcome(game_id=game_id, ts=_now_iso(), status="WIN")

    elif game.status == GameStatus.LOST:
        log.info(f"LOST user={user_id} gid={game_id}")
        STATS_DB.outcome(game_id=game_id, ts=_now_iso(), status="LOST")

    # Game state (the shared contract) + app config (server-only feature flags),
    # inlined separately into the shell. render.js builds the view from both.
    state = serialize_game(board, game, game_id)
    config = {
        "reset_policy": settings.RESET_POLICY,
        "enable_survey": bool(settings.ENABLE_SURVEY),
        "survey_url": settings.SURVEY_URL,
    }
    return attach_user_cookie(
        templates.TemplateResponse(request, "game.html", {"state": state, "config": config}),
        user_id,
        request,
    )


@app.post("/move")
async def move_post(
    cmd: str = Form(...),
    game_id: Optional[str] = Query(None, alias="game_id"),
):
    """
    Handle a single move command from the frontend.

    Parameters
    ----------
    cmd : str
        The command string submitted from the UI (e.g., "M 2,3", "X 1,1", "P 4,4").
    game_id : Optional[str]
        The unique identifier of the game (passed as query param).

    Returns
    -------
    RedirectResponse
        Redirects back to the game view after applying the move.
    """
    if not game_id or game_id not in GAMES:
        return RedirectResponse("/setup", status_code=303)

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
        log.exception(f"MOVE error gid={game_id} cmd='{cmd}' err={e}")

    # Update heartbeat and last_seen after any move
    GAMES[game_id]["last_seen"] = datetime.now(timezone.utc)
    STATS_DB.heartbeat(game_id=game_id, ts=_now_iso())

    return RedirectResponse(f"/game?game_id={game_id}", status_code=303)


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
            cfg["rows"], cfg["cols"], cfg["mines"], cfg["ent_level"], cfg["win"], cfg["moves"]
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
        {},
    )


@app.post("/admin/update_settings")
async def update_settings(
    request: Request,
    ENABLE_HELP: Optional[str] = Form(None),
    ENABLE_ABOUT: Optional[str] = Form(None),
    ENABLE_TUTORIAL: Optional[str] = Form(None),
    ENABLE_SURVEY: Optional[str] = Form(None),
    RESET_POLICY: str = Form("sandbox"),
):
    if not admin_authed(request):
        return RedirectResponse("/admin/login", status_code=303)

    # update settings
    settings.ENABLE_HELP = bool(ENABLE_HELP)
    settings.ENABLE_ABOUT = bool(ENABLE_ABOUT)
    settings.ENABLE_TUTORIAL = bool(ENABLE_TUTORIAL)
    settings.ENABLE_SURVEY = bool(ENABLE_SURVEY)
    settings.RESET_POLICY = RESET_POLICY

    # update template globals
    templates.env.globals["FEATURES"].update(
        ENABLE_HELP=settings.ENABLE_HELP,
        ENABLE_ABOUT=settings.ENABLE_ABOUT,
        ENABLE_TUTORIAL=settings.ENABLE_TUTORIAL,
        ENABLE_SURVEY=settings.ENABLE_SURVEY,
        RESET_POLICY=settings.RESET_POLICY,
    )

    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/db_view", response_class=HTMLResponse)
def view_db(request: Request):
    if not admin_authed(request):
        return RedirectResponse("/admin/login", status_code=303)

    cur = STATS_DB._db.cursor()
    cur.execute("SELECT * FROM games ORDER BY created_at DESC LIMIT 100")
    rows = cur.fetchall()

    if not rows:
        return HTMLResponse("<p>No games found.</p>")

    # convert sqlite3.Row → dict with formatted datetimes
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
        {"rows": formatted_rows},
    )


@app.get("/admin/db_download")
def download_db(request: Request):
    if not admin_authed(request):
        return RedirectResponse("/admin/login", status_code=303)

    # fetch rows
    cur = STATS_DB._db.cursor()
    cur.execute("SELECT * FROM games")
    rows = cur.fetchall()

    # write CSV into memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(rows[0].keys() if rows else [])
    for row in rows:
        writer.writerow([row[k] for k in row.keys()])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=qms_games.csv"},
    )


@app.get("/about", response_class=HTMLResponse)
async def about_get(request: Request, game_id: Optional[str] = Query(None)):
    prune_stale_games()

    user_id = ensure_user_id(request)
    log.info(f"User {user_id} opened about page")
    resp = templates.TemplateResponse(
        request,
        "about.html",
        {"game_id": game_id},
    )
    return attach_user_cookie(resp, user_id, request)
