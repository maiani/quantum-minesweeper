from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import logging
import re

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4

from qminesweeper.board import QMineSweeperBoard
from qminesweeper.game import (
    QMineSweeperGame, GameConfig, WinCondition, MoveSet, GameStatus
)
from qminesweeper.stim_backend import StimBackend

# --------- App & assets ---------
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-me-in-prod")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("qminesweeper.web")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Optional: quiet favicon 404s if no file present
@app.get("/favicon.ico", include_in_schema=False)
def _favicon():
    ico = STATIC_DIR / "favicon.ico"
    if ico.exists():
        return Response((ico).read_bytes(), media_type="image/x-icon")
    return PlainTextResponse("", status_code=204)

# --------- Session helpers ---------
GAMES: dict[str, dict] = {}

def get_sid(request: Request) -> str:
    sid = request.session.get("sid")
    if not sid:
        sid = str(uuid4())
        request.session["sid"] = sid
        log.info(f"SID created: {sid}")
    return sid

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
    # UI uses 1-based; convert to 0-based
    m = re.match(r"^\s*(\d+)\s*,\s*(\d+)\s*$", token)
    if not m:
        raise ValueError(f"Bad coord '{token}' (expected 'r,c')")
    r = int(m.group(1)) - 1
    c = int(m.group(2)) - 1
    return r, c

def parse_cmd(cmd: str):
    """
    Returns a tuple describing the command:
        ("M", (r,c))
        ("P", (r,c))
        ("G1", (gate, (r,c)))
        ("G2", (gate, (r1,c1), (r2,c2)))
    Raises ValueError on invalid syntax.
    """
    if not cmd or not cmd.strip():
        raise ValueError("Empty command")
    s = cmd.strip()
    # allow bare "r,c" as shorthand for measure
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
        rc1 = _parse_rc(parts[1])
        rc2 = _parse_rc(parts[2])
        return ("G2", (op, rc1, rc2))

    raise ValueError(f"Unrecognized command: '{cmd}'")

# --------- Routes ---------
@app.get("/health")
def health():
    return PlainTextResponse("ok")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")
    return RedirectResponse("/game")

@app.get("/setup", response_class=HTMLResponse, name="setup_get")
async def setup_get(request: Request):
    log.info("GET /setup")
    return templates.TemplateResponse("setup.html", {
        "request": request,
        "theme": request.session.get("theme", "dark"),
    })

@app.post("/setup", name="setup_post")
async def setup_post(
    request: Request,
    rows: int = Form(...),
    cols: int = Form(...),
    bombs: int = Form(...),
    ent_level: int = Form(...),
    win_condition: str = Form(...),   # "identify" | "clear"
    move_set: str = Form(...),        # "classic" | "one" | "one_complete" | "two"
):
    sid = get_sid(request)

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
        "config": {"rows": rows, "cols": cols, "bombs": bombs, "ent_level": ent_level,
                   "win": win, "moves": mv},
    }
    request.session.setdefault("theme", "dark")

    log.info(f"SETUP sid={sid} rows={rows} cols={cols} bombs={bombs} ent={ent_level} "
             f"win={win.name} moves={mv.name}")

    return RedirectResponse("/game", status_code=303)

@app.get("/game", response_class=HTMLResponse, name="game_get")
async def game_get(request: Request):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]

    # Build dynamic tools from MoveSet (for frontend toolbar only)
    ms = game.cfg.move_set
    tools = ["M", "P"]
    if ms in (MoveSet.ONE_QUBIT, MoveSet.ONE_QUBIT_COMPLETE, MoveSet.TWO_QUBIT):
        tools += ["X", "Y", "Z", "H", "S"]
    if ms in (MoveSet.ONE_QUBIT_COMPLETE, MoveSet.TWO_QUBIT):
        tools += ["SDG", "SX", "SXDG", "SY", "SYDG"]
    if ms == MoveSet.TWO_QUBIT:
        tools += ["CX", "CY", "CZ", "SWAP"]

    # Build grid
    grid = []
    numeric = board.export_numeric_grid()
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

    log.info(f"GET /game sid={sid} status={game.status.name}")

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "grid": grid,
            "rows": board.rows,
            "cols": board.cols,
            "status": game.status.name,
            "tools": tools,       # purely for client toolbar
            "suid": sid,          # front-end will include this with moves
            "theme": request.session.get("theme", "dark"),
        },
    )

@app.post("/move", name="move_post")
async def move_post(
    request: Request,
    cmd: str = Form(...),
    suid: Optional[str] = Form(None),
):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup", status_code=303)

    # suid is informational; we rely on session cookie for actual identity
    if suid and suid != sid:
        log.warning(f"Move suid mismatch: form_suid={suid} cookie_sid={sid}")

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]

    try:
        kind, payload = parse_cmd(cmd)
    except ValueError as e:
        log.error(f"MOVE PARSE ERROR sid={sid} cmd='{cmd}' err={e}")
        return RedirectResponse("/game", status_code=303)

    log.info(f"MOVE sid={sid} cmd='{cmd}' parsed={kind} payload={payload}")

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
        log.exception(f"MOVE EXEC ERROR sid={sid} cmd='{cmd}' err={e}")

    return RedirectResponse("/game", status_code=303)

# ---------- Legacy /game POST for non-move actions ----------
@app.post("/game", name="game_post")
async def game_post(
    request: Request,
    action: str = Form(...),
):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup", status_code=303)

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]
    cfg = GAMES[sid]["config"]

    if action == "reset":
        board.reset()
        game.status = GameStatus.ONGOING
        log.info(f"ACTION sid={sid} reset -> status={game.status.name}")

    elif action == "new_same":
        board, game = build_board_and_game(cfg["rows"], cfg["cols"], cfg["bombs"], cfg["ent_level"],
                                           cfg["win"], cfg["moves"])
        GAMES[sid]["board"] = board
        GAMES[sid]["game"] = game
        log.info(f"ACTION sid={sid} new_same created")

    elif action == "new_rules":
        log.info(f"ACTION sid={sid} new_rules -> redirect /setup")
        return RedirectResponse("/setup", status_code=303)

    elif action == "toggle_theme":
        theme = request.session.get("theme", "dark")
        request.session["theme"] = "light" if theme == "dark" else "dark"
        log.info(f"ACTION sid={sid} toggle_theme -> {request.session['theme']}")

    return RedirectResponse("/game", status_code=303)
