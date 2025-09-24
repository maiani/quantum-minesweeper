# qminesweeper/webapp.py
from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple, cast
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
from markdown.extensions.toc import TocExtension

from qminesweeper import __version__
from qminesweeper.auth import enable_basic_auth
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.database import get_store
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
    exclude_paths=["/health", "/static/*"],
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

templates.env.globals["FEATURES"] = {
    "ENABLE_HELP": settings.ENABLE_HELP,
    "ENABLE_TUTORIAL": settings.ENABLE_TUTORIAL,
    "TUTORIAL_URL": settings.TUTORIAL_URL,
    "RESET_POLICY": settings.RESET_POLICY,
}
templates.env.globals["online_count"] = lambda: STATS_DB.online_active()

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


# --------- In-memory game store ---------
# game_id -> {board, game, config}
GAMES: dict[str, dict] = {}


# --------- Helpers ---------
def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clue_color(val: float) -> str:
    v = max(0.0, min(val / 8.0, 1.0))
    r = int(255 * v)
    g = int(255 * (1.0 - v))
    return f"rgb({r},{g},0)"


def build_board_and_game(rows: int, cols: int, mines: int, ent_level: int, win: WinCondition, moves: MoveSet):
    board = QMineSweeperBoard(rows, cols, backend=StimBackend(), flood_fill=True)
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
    stale_ids = [gid for gid, rec in GAMES.items()
                 if rec.get("last_seen") and rec["last_seen"] < cutoff]
    for gid in stale_ids:
        game = GAMES[gid]["game"]
        if game.status == GameStatus.ONGOING:
            STATS_DB.outcome(game_id=gid, ts=_now_iso(), status="ABANDONED")
        GAMES.pop(gid, None)

    # Clean database store
    n = STATS_DB.prune_abandoned(minutes=settings.ABANDON_THRESHOLD_MIN)
    if n:
        log.info(f"Pruned {n} abandoned games (scheduled)")



# ----- Command parsing -----
_SINGLE_Q = {"X", "Y", "Z", "H", "S", "SDG", "SX", "SXDG", "SY", "SYDG"}
_TWO_Q = {"CX", "CY", "CZ", "SWAP"}


def _parse_rc(token: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d+)\s*,\s*(\d+)\s*$", token)
    if not m:
        raise ValueError(f"Bad coord '{token}' (expected 'r,c')")
    return int(m.group(1)) - 1, int(m.group(2)) - 1


def parse_cmd(cmd: str):
    if not cmd or not cmd.strip():
        raise ValueError("Empty command")
    s = cmd.strip()
    if re.match(r"^\s*\d+\s*,\s*\d+\s*$", s):
        return ("M", _parse_rc(s))
    parts = s.split()
    op = parts[0].upper()
    if op == "M" and len(parts) == 2:
        return ("M", _parse_rc(parts[1]))
    if op == "P" and len(parts) == 2:
        return ("P", _parse_rc(parts[1]))
    if op in _SINGLE_Q and len(parts) == 2:
        return ("G1", (op, _parse_rc(parts[1])))
    if op in _TWO_Q and len(parts) == 3:
        return ("G2", (op, _parse_rc(parts[1]), _parse_rc(parts[2])))
    raise ValueError(f"Unrecognized command: '{cmd}'")


# --------- Routes ---------
@app.get("/health")
def health():
    return PlainTextResponse("ok")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    prune_stale_games()

    # Stateless: always go to setup with a fresh game_id in URL
    user_id = ensure_user_id(request)
    game_id = str(uuid4())
    resp = RedirectResponse(f"/setup?game_id={game_id}")
    return attach_user_cookie(resp, user_id, request)


@app.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request, game_id: Optional[str] = Query(None)):
    prune_stale_games()

    user_id = ensure_user_id(request)
    game_id = game_id or str(uuid4())
    log.info(f"User {user_id} -> setup gid={game_id}")
    resp = templates.TemplateResponse(
        "setup.html",
        {
            "request": request,
            "game_id": game_id,
        },
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

    board, game = build_board_and_game(rows, cols, mines, ent_level, win, mv)
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

    grid = board.export_numeric_grid().tolist()
    mines_exp = board.expected_mines()
    ent_score = board.entanglement_score("mean") * board.n

    # Persist terminal outcome once it happens
    if game.status == GameStatus.WIN:
        log.info(f"WIN user={user_id} gid={game_id}")
        STATS_DB.outcome(game_id=game_id, ts=_now_iso(), status="WIN")

    elif game.status == GameStatus.LOST:
        log.info(f"LOST user={user_id} gid={game_id}")
        STATS_DB.outcome(game_id=game_id, ts=_now_iso(), status="LOST")


    return attach_user_cookie(
        templates.TemplateResponse(
            "game.html",
            {
                "request": request,
                "grid": grid,
                "rows": board.rows,
                "cols": board.cols,
                "status": game.status.name,
                "moveset": game.cfg.move_set.name,
                "game_id": game_id,
                "mines_exp": mines_exp,
                "ent_measure": ent_score,
            },
        ),
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

    game: QMineSweeperGame = GAMES[game_id]["game"]

    try:
        kind, payload = parse_cmd(cmd)

        if kind == "M":
            # Measurement: payload is a (row, col) tuple
            rc = cast(Tuple[int, int], payload)
            game.cmd_measure(*rc)
            STATS_DB.increment_move(game_id=game_id, kind="measure")

        elif kind == "P":
            # Pin toggle: payload is a (row, col) tuple
            rc = cast(Tuple[int, int], payload)
            game.cmd_toggle_pin(*rc)
            # no counter: pinning is not tracked

        elif kind == "G1":
            gate, rc = payload  # type: ignore[misc]
            gate = cast(str, gate)  # ensure type checker sees this as str
            game.cmd_gate(gate, [cast(Tuple[int, int], rc)])
            STATS_DB.increment_move(game_id=game_id, kind="gate")

        elif kind == "G2":
            gate, rc1, rc2 = payload  # type: ignore[misc]
            gate = cast(str, gate)  # ensure type checker sees this as str
            game.cmd_gate(
                gate,
                [cast(Tuple[int, int], rc1), cast(Tuple[int, int], rc2)],
            )
            STATS_DB.increment_move(game_id=game_id, kind="gate")

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
            board.reset()
            game.status = GameStatus.ONGOING
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
        # new setup flow (new game_id will be created during POST /setup)
        return RedirectResponse(f"/setup?game_id={str(uuid4())}", status_code=303)

    return RedirectResponse(f"/game?game_id={game_id}", status_code=303)


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
}
templates.env.globals["docs"] = DOCS


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, admin_pass: str = Query(...)):
    if admin_pass != settings.ADMIN_PASS:
        return PlainTextResponse("Forbidden", status_code=403)

    return templates.TemplateResponse(
        "admin_home.html",
        {"request": request},
    )

@app.post("/admin/update_settings")
async def update_settings(
    request: Request,
    admin_pass: str = Form(...),
    ENABLE_HELP: Optional[str] = Form(None),
    ENABLE_TUTORIAL: Optional[str] = Form(None),
    RESET_POLICY: str = Form("sandbox"),
):
    if admin_pass != settings.ADMIN_PASS:
        return PlainTextResponse("Forbidden", status_code=403)

    # update settings
    settings.ENABLE_HELP = bool(ENABLE_HELP)
    settings.ENABLE_TUTORIAL = bool(ENABLE_TUTORIAL)
    settings.RESET_POLICY = RESET_POLICY

    # update template globals
    templates.env.globals["FEATURES"].update(
        ENABLE_HELP=settings.ENABLE_HELP,
        ENABLE_TUTORIAL=settings.ENABLE_TUTORIAL,
        RESET_POLICY=settings.RESET_POLICY,
    )

    return RedirectResponse(f"/admin?admin_pass={admin_pass}", status_code=303)


@app.get("/admin/db_view", response_class=HTMLResponse)
def view_db(request: Request, admin_pass: str = Query(...)):
    if admin_pass != settings.ADMIN_PASS:
        return PlainTextResponse("Forbidden", status_code=403)

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
        "db_view.html",
        {"request": request, "rows": formatted_rows},
    )

@app.get("/admin/db_download")
def download_db(request: Request, admin_pass: str = Query(...)):
    if admin_pass != settings.ADMIN_PASS:
        return PlainTextResponse("Forbidden", status_code=403)

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