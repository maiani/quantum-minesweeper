# qminesweeper/webapp.py
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import markdown
from markdown.extensions.toc import TocExtension

from qminesweeper import __version__
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import (
    QMineSweeperGame, GameConfig, WinCondition, MoveSet, GameStatus
)
from qminesweeper.stim_backend import StimBackend
from qminesweeper.auth import enable_basic_auth
from qminesweeper.logging_config import setup_logging
from qminesweeper.settings import get_settings

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

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("qminesweeper.web")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DOCS_DIR = BASE_DIR / "docs"
HELP_DIR = DOCS_DIR / "help"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["now"] = datetime.now
templates.env.globals["version"] = __version__

templates.env.globals["FEATURES"] = {
    "enable_help": settings.ENABLE_HELP,
    "enable_tutorial": settings.ENABLE_TUTORIAL,
    "tutorial_url": settings.TUTORIAL_URL,
}

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
        key=USER_COOKIE, value=user_id, path="/",
        httponly=True, samesite="lax",
        secure=(request.url.scheme == "https"),
    )
    return resp

# --------- Demo in-memory game store ---------
GAMES: dict[str, dict] = {}  # suid -> {board, game, config}

# --------- Helpers ---------
def clue_color(val: float) -> str:
    v = max(0.0, min(val / 8.0, 1.0))
    r = int(255 * v); g = int(255 * (1.0 - v))
    return f"rgb({r},{g},0)"

def build_board_and_game(rows:int, cols:int, mines:int, ent_level:int,
                         win:WinCondition, moves:MoveSet):
    board = QMineSweeperBoard(rows, cols, backend=StimBackend(), flood_fill=True)
    if ent_level == 0:
        board.span_classical_mines(mines)
    else:
        board.span_random_stabilizer_mines(mines, level=ent_level)
    board.set_clue_basis("Z")
    game = QMineSweeperGame(board, GameConfig(win_condition=win, move_set=moves))
    return board, game

# ----- Command parsing -----
_SINGLE_Q = {"X","Y","Z","H","S","SDG","SX","SXDG","SY","SYDG"}
_TWO_Q = {"CX","CY","CZ","SWAP"}

def _parse_rc(token: str) -> Tuple[int,int]:
    m = re.match(r"^\s*(\d+)\s*,\s*(\d+)\s*$", token)
    if not m:
        raise ValueError(f"Bad coord '{token}' (expected 'r,c')")
    return int(m.group(1))-1, int(m.group(2))-1

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
    # Stateless: always go to setup with a fresh suid in URL
    user_id = ensure_user_id(request)
    suid = str(uuid4())
    resp = RedirectResponse(f"/setup?suid={suid}")
    return attach_user_cookie(resp, user_id, request)

@app.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request, suid: Optional[str] = Query(None)):
    user_id = ensure_user_id(request)
    suid = suid or str(uuid4())
    log.info(f"User {user_id} -> setup sid={suid}")
    resp = templates.TemplateResponse("setup.html", {
        "request": request,
        "suid": suid,
    })
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
    suid: Optional[str] = Query(None, alias="suid"),
):
    user_id = ensure_user_id(request)
    suid = suid or str(uuid4())

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
    }.get(move_set.lower(), MoveSet.CLASSIC)

    board, game = build_board_and_game(rows, cols, mines, ent_level, win, mv)
    GAMES[suid] = {
        "board": board,
        "game": game,
        "config": {"rows": rows, "cols": cols, "mines": mines,
                   "ent_level": ent_level, "win": win, "moves": mv},
    }

    log.info(f"SETUP user={user_id} sid={suid} rows={rows} cols={cols} mines={mines} "
             f"ent={ent_level} win={win.name} moves={mv.name}")

    return attach_user_cookie(RedirectResponse(f"/game?suid={suid}", status_code=303),
                              user_id, request)

@app.get("/game", response_class=HTMLResponse)
async def game_get(request: Request, suid: Optional[str] = Query(None, alias="suid")):
    user_id = ensure_user_id(request)
    if not suid or suid not in GAMES:
        return attach_user_cookie(RedirectResponse("/setup", status_code=303), user_id, request)

    board: QMineSweeperBoard = GAMES[suid]["board"]
    game: QMineSweeperGame = GAMES[suid]["game"]

    grid = board.export_numeric_grid().tolist()
    mines_exp = board.expected_mines()
    ent_score = board.entanglement_score("mean") * board.n

    if game.status == GameStatus.WIN:
        log.info(f"WIN user={user_id} sid={suid}")
    elif game.status == GameStatus.LOST:
        log.info(f"LOST user={user_id} sid={suid}")

    return attach_user_cookie(templates.TemplateResponse("game.html", {
        "request": request,
        "grid": grid, 
        "rows": board.rows, "cols": board.cols,
        "status": game.status.name,
        "moveset": game.cfg.move_set.name,
        "suid": suid,
        "mines_exp": mines_exp,
        "ent_measure": ent_score,
    }), user_id, request)

@app.post("/move")
async def move_post(cmd: str = Form(...), suid: Optional[str] = Query(None, alias="suid")):
    if not suid or suid not in GAMES:
        return RedirectResponse("/setup", status_code=303)

    board: QMineSweeperBoard = GAMES[suid]["board"]
    game: QMineSweeperGame = GAMES[suid]["game"]

    try:
        kind, payload = parse_cmd(cmd)
        if kind == "M":
            game.cmd_measure(*payload)
        elif kind == "P":
            game.cmd_toggle_pin(*payload)
        elif kind == "G1":
            gate, rc = payload
            game.cmd_gate(gate, [rc])
        elif kind == "G2":
            gate, rc1, rc2 = payload
            game.cmd_gate(gate, [rc1, rc2])
    except Exception as e:
        log.exception(f"MOVE error sid={suid} cmd='{cmd}' err={e}")

    return RedirectResponse(f"/game?suid={suid}", status_code=303)

@app.post("/game")
async def game_post(action: str = Form(...), suid: Optional[str] = Query(None, alias="suid")):
    if not suid or suid not in GAMES:
        return RedirectResponse("/setup", status_code=303)

    board: QMineSweeperBoard = GAMES[suid]["board"]
    game: QMineSweeperGame = GAMES[suid]["game"]
    cfg = GAMES[suid]["config"]

    if action == "reset":
        board.reset()
        game.status = GameStatus.ONGOING
    elif action == "new_same":
        board, game = build_board_and_game(
            cfg["rows"], cfg["cols"], cfg["mines"], cfg["ent_level"], cfg["win"], cfg["moves"]
        )
        GAMES[suid]["board"] = board
        GAMES[suid]["game"] = game
    elif action == "new_rules":
        return RedirectResponse(f"/setup?suid={suid}", status_code=303)

    return RedirectResponse(f"/game?suid={suid}", status_code=303)

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
                lines = lines[i+1:]
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
        extension_configs={
            "pymdownx.arithmatex": {"generic": True}
        }
    )
    return title, html


DOCS_DIR = BASE_DIR / "docs"

DOCS = {
    "simple_setup": render_markdown(DOCS_DIR / "simple_setup.md")[1],
    "advanced_setup": render_markdown(DOCS_DIR / "advanced_setup.md")[1],
}
templates.env.globals["docs"] = DOCS

@app.get("/help/{obj_id}", response_class=JSONResponse)
async def help_content(obj_id: str):
    base = HELP_DIR / obj_id
    text_path = base / "text.md"
    visual_path = base / "visual.html"

    title, text_html = render_markdown(text_path, strip_title=True)
    visual_html = "<div>No visual available.</div>"

    if visual_path.exists():
        visual_html = visual_path.read_text(encoding="utf-8")

    return {"title": title, "text": text_html, "visual": visual_html}
