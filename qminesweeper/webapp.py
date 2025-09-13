from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import os
import logging
import re
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from qminesweeper import __version__
from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import (
    QMineSweeperGame, GameConfig, WinCondition, MoveSet, GameStatus
)
from qminesweeper.stim_backend import StimBackend
from qminesweeper.auth import enable_basic_auth  

# --------- App & assets ---------
app = FastAPI()
enable_basic_auth(app, exclude_paths=["/health", "/favicon.ico", "/static/*"])

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("qminesweeper.web")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["now"] = datetime.now
templates.env.globals["version"] = __version__

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --------- Cookies ---------
USER_COOKIE = "qmsuser"
GAME_COOKIE = "qmsid"     # still used to remember last suid
THEME_COOKIE = "theme"

# --------- State ---------
GAMES: dict[str, dict] = {}

# --------- Helpers ---------
def ensure_user_id(request: Request) -> str:
    user_id = request.cookies.get(USER_COOKIE)
    if not user_id:
        user_id = str(uuid4())
        log.info(f"New user_id created: {user_id}")
    return user_id

def attach_user_cookie(response: Response, user_id: str, request: Request) -> Response:
    secure = (request.url.scheme == "https")
    response.set_cookie(
        key=USER_COOKIE,
        value=user_id,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    return response

def get_theme(request: Request) -> str:
    return request.cookies.get(THEME_COOKIE, "dark")

def attach_theme_cookie(response: Response, theme: str, request: Request) -> Response:
    secure = (request.url.scheme == "https")
    response.set_cookie(
        key=THEME_COOKIE,
        value=theme,
        path="/",
        httponly=False,   # allow JS toggle if needed
        secure=secure,
        samesite="lax",
    )
    return response

# --------- Game building ---------
def clue_color(val: float) -> str:
    v = max(0.0, min(val / 8.0, 1.0))
    r = int(255 * v)
    g = int(255 * (1.0 - v))
    return f"rgb({r},{g},0)"

def build_board_and_game(rows:int, cols:int, bombs:int, ent_level:int,
                         win:WinCondition, moves:MoveSet):
    board = QMineSweeperBoard(rows, cols, backend=StimBackend(), flood_fill=True)
    if ent_level == 0:
        board.span_classical_bombs(bombs)
    else:
        board.span_random_stabilizer_bombs(bombs, level=ent_level)
    board.set_clue_basis("Z")
    game = QMineSweeperGame(board, GameConfig(win_condition=win, move_set=moves))
    return board, game

# --------- Command parsing ---------
_SINGLE_Q = {"X","Y","Z","H","S","SDG","SX","SXDG","SY","SYDG"}
_TWO_Q = {"CX","CY","CZ","SWAP"}

def _parse_rc(token: str) -> Tuple[int,int]:
    m = re.match(r"^\s*(\d+)\s*,\s*(\d+)\s*$", token)
    if not m:
        raise ValueError(f"Bad coord '{token}' (expected 'r,c')")
    r = int(m.group(1)) - 1
    c = int(m.group(2)) - 1
    return r, c

def parse_cmd(cmd: str):
    if not cmd or not cmd.strip():
        raise ValueError("Empty command")
    s = cmd.strip()
    if re.match(r"^\s*\d+\s*,\s*\d+\s*$", s):
        r, c = _parse_rc(s)
        return ("M", (r, c))
    parts = s.split()
    op = parts[0].upper()
    if op == "M" and len(parts) == 2:
        return ("M", _parse_rc(parts[1]))
    if op == "P" and len(parts) == 2:
        return ("P", _parse_rc(parts[1]))
    if op in _SINGLE_Q and len(parts) == 2:
        return ("G1", (op, _parse_rc(parts[1])))
    if op in _TWO_Q and len(parts) == 3:
        rc1 = _parse_rc(parts[1]); rc2 = _parse_rc(parts[2])
        return ("G2", (op, rc1, rc2))
    raise ValueError(f"Unrecognized command: '{cmd}'")

# --------- Routes ---------
@app.get("/health")
def health():
    return PlainTextResponse("ok")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user_id = ensure_user_id(request)
    resp = RedirectResponse("/setup")
    return attach_user_cookie(resp, user_id, request)

@app.get("/setup", response_class=HTMLResponse, name="setup_get")
async def setup_get(request: Request):
    user_id = ensure_user_id(request)
    sid = str(uuid4())
    log.info(f"User {user_id} -> setup with new sid={sid}")
    resp = templates.TemplateResponse("setup.html", {
        "request": request,
        "theme": get_theme(request),
        "suid": sid,
    })
    resp.set_cookie(GAME_COOKIE, sid, path="/", httponly=True, samesite="lax")
    return attach_user_cookie(resp, user_id, request)

@app.post("/setup", name="setup_post")
async def setup_post(
    request: Request,
    rows: int = Form(...),
    cols: int = Form(...),
    bombs: int = Form(...),
    ent_level: int = Form(...),
    win_condition: str = Form(...),
    move_set: str = Form(...),
    suid: Optional[str] = Form(None),
):
    user_id = ensure_user_id(request)
    sid = suid or str(uuid4())

    win = WinCondition.CLEAR if win_condition.lower() == "clear" else WinCondition.IDENTIFY
    mv = {
        "classic": MoveSet.CLASSIC,
        "one": MoveSet.ONE_QUBIT,
        "one_complete": MoveSet.ONE_QUBIT_COMPLETE,
        "two": MoveSet.TWO_QUBIT,
    }.get(move_set.lower(), MoveSet.CLASSIC)

    board, game = build_board_and_game(rows, cols, bombs, ent_level, win, mv)
    GAMES[sid] = {
        "board": board,
        "game": game,
        "config": {"rows": rows, "cols": cols, "bombs": bombs,
                   "ent_level": ent_level, "win": win, "moves": mv},
    }

    log.info(f"SETUP user={user_id} sid={sid} rows={rows} cols={cols} bombs={bombs} "
             f"ent={ent_level} win={win.name} moves={mv.name}")

    resp = RedirectResponse("/game", status_code=303)
    resp.set_cookie(GAME_COOKIE, sid, path="/", httponly=True, samesite="lax")
    return attach_user_cookie(resp, user_id, request)

@app.get("/game", response_class=HTMLResponse, name="game_get")
async def game_get(request: Request):
    user_id = ensure_user_id(request)
    sid = request.cookies.get(GAME_COOKIE)
    if not sid or sid not in GAMES:
        resp = RedirectResponse("/setup")
        return attach_user_cookie(resp, user_id, request)

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]

    numeric = board.export_numeric_grid()
    grid = []
    for r in range(board.rows):
        row = []
        for c in range(board.cols):
            val = numeric[r, c]
            cell = {"r": r, "c": c, "text": "", "style": ""}
            if val == -1:
                cell["text"] = "■"
                cell["style"] = "color:var(--tile-muted);"
            elif val == -2:
                cell["text"] = "⚑"
                cell["style"] = "color:var(--pin);"
            elif val == 9.0:
                cell["text"] = "💥"
                cell["style"] = "font-weight:700;color:var(--boom);"
            elif val == 0.0:
                cell["text"] = "&nbsp;"
                cell["style"] = "background:var(--zero-bg);"
            else:
                cell["text"] = f"{val:.1f}"
                cell["style"] = f"color:{clue_color(val)};"
            row.append(cell)
        grid.append(row)

    result_msg = None
    if game.status == GameStatus.WIN:
        result_msg = "You win! 🎉"
    elif game.status == GameStatus.LOST:
        result_msg = "You lost! 💥"

    resp = templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "grid": grid,
            "rows": board.rows,
            "cols": board.cols,
            "status": game.status.name,
            "moveset": game.cfg.move_set.name,
            "suid": sid,
            "theme": get_theme(request),
            "result_msg": result_msg,
        },
    )
    return attach_user_cookie(resp, user_id, request)

@app.post("/move", name="move_post")
async def move_post(
    request: Request,
    cmd: str = Form(...),
    suid: Optional[str] = Form(None),
):
    user_id = ensure_user_id(request)
    sid = suid or request.cookies.get(GAME_COOKIE)
    if not sid or sid not in GAMES:
        log.warning(f"MOVE user={user_id} invalid sid={sid}")
        resp = RedirectResponse("/setup", status_code=303)
        return attach_user_cookie(resp, user_id, request)

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]

    try:
        kind, payload = parse_cmd(cmd)
    except ValueError as e:
        log.error(f"MOVE parse error user={user_id} sid={sid} cmd='{cmd}' err={e}")
        resp = RedirectResponse("/game", status_code=303)
        return attach_user_cookie(resp, user_id, request)

    log.info(f"MOVE user={user_id} sid={sid} cmd='{cmd}' parsed={kind} payload={payload}")

    try:
        if kind == "M":
            (r, c) = payload
            game.cmd_measure(r, c)
        elif kind == "P":
            (r, c) = payload
            game.cmd_toggle_pin(r, c)
        elif kind == "G1":
            gate, (r, c) = payload
            game.cmd_gate(gate, [(r, c)])
        elif kind == "G2":
            gate, (r1, c1), (r2, c2) = payload
            game.cmd_gate(gate, [(r1, c1), (r2, c2)])
    except Exception as e:
        log.exception(f"MOVE exec error user={user_id} sid={sid} cmd='{cmd}' err={e}")

    resp = RedirectResponse("/game", status_code=303)
    return attach_user_cookie(resp, user_id, request)

@app.post("/game", name="game_post")
async def game_post(
    request: Request,
    action: str = Form(...),
    suid: Optional[str] = Form(None),
):
    user_id = ensure_user_id(request)
    sid = suid or request.cookies.get(GAME_COOKIE)
    if not sid or sid not in GAMES:
        log.warning(f"ACTION user={user_id} invalid sid={sid}")
        resp = RedirectResponse("/setup", status_code=303)
        return attach_user_cookie(resp, user_id, request)

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]
    cfg = GAMES[sid]["config"]

    if action == "reset":
        board.reset()
        game.status = GameStatus.ONGOING
        log.info(f"ACTION user={user_id} sid={sid} reset -> status={game.status.name}")

    elif action == "new_same":
        board, game = build_board_and_game(cfg["rows"], cfg["cols"], cfg["bombs"], cfg["ent_level"],
                                           cfg["win"], cfg["moves"])
        GAMES[sid]["board"] = board
        GAMES[sid]["game"] = game
        log.info(f"ACTION user={user_id} sid={sid} new_same")

    elif action == "new_rules":
        log.info(f"ACTION user={user_id} sid={sid} new_rules -> /setup")
        resp = RedirectResponse("/setup", status_code=303)
        return attach_user_cookie(resp, user_id, request)

    elif action == "toggle_theme":
        theme = get_theme(request)
        new_theme = "light" if theme == "dark" else "dark"
        log.info(f"ACTION user={user_id} sid={sid} toggle_theme -> {new_theme}")
        resp = RedirectResponse("/game", status_code=303)
        resp = attach_theme_cookie(resp, new_theme, request)
        return attach_user_cookie(resp, user_id, request)

    resp = RedirectResponse("/game", status_code=303)
    return attach_user_cookie(resp, user_id, request)
