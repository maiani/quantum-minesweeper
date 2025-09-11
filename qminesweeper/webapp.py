from __future__ import annotations
from pathlib import Path
from typing import Optional
import logging  # DEBUG
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

# DEBUG: basic logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("qminesweeper.web")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Static mount
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
        log.info(f"SID created: {sid}")  # DEBUG
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
    log.info("GET /setup")  # DEBUG
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
    request.session.setdefault("tool", "M")
    request.session.setdefault("theme", "dark")

    log.info(f"SETUP sid={sid} rows={rows} cols={cols} bombs={bombs} ent={ent_level} "
             f"win={win.name} moves={mv.name}")  # DEBUG

    return RedirectResponse("/game", status_code=303)

@app.get("/game", response_class=HTMLResponse, name="game_get")
async def game_get(request: Request):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]

    # Build dynamic tools from MoveSet (like TUI)
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

    log.info(f"GET /game sid={sid} status={game.status.name} "
             f"tool={request.session.get('tool','M')}")  # DEBUG

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "grid": grid,
            "rows": board.rows,
            "cols": board.cols,
            "status": game.status.name,
            "tools": tools,
            "current_tool": request.session.get("tool", "M"),
            "theme": request.session.get("theme", "dark"),
        },
    )

@app.post("/game", name="game_post")
async def game_post(
    request: Request,
    action: str = Form(...),
    # r,c arrive as QUERY params via formaction
    r: Optional[int] = Query(None),
    c: Optional[int] = Query(None),
    r2: Optional[int] = Query(None),
    c2: Optional[int] = Query(None),
    tool: Optional[str] = Query(None),
):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup", status_code=303)

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]
    cfg = GAMES[sid]["config"]

    # DEBUG: log incoming action & params
    log.info(f"POST /game sid={sid} action={action} "
             f"r={r} c={c} r2={r2} c2={c2} "
             f"tool_q={tool} tool_session={request.session.get('tool','M')} "
             f"status_before={game.status.name}")

    if action == "cell":
        # Prefer tool from the query (button) else fall back to session
        t = (tool or request.session.get("tool", "M") or "M").upper()
        log.info(f"MOVE sid={sid} kind=CELL tool={t} r={r} c={c} r2={r2} c2={c2}")  # DEBUG

        if t in ("CX", "CY", "CZ", "SWAP"):
            if r is not None and c is not None and r2 is not None and c2 is not None:
                game.cmd_gate(t, [(r, c), (r2, c2)])

        elif t == "P":
            if r is not None and c is not None:
                game.cmd_toggle_pin(r, c)

        elif t == "M":
            if r is not None and c is not None:
                game.cmd_measure(r, c)

        elif t in ("X", "Y", "Z", "H", "S", "SDG", "SX", "SXDG", "SY", "SYDG"):
            if r is not None and c is not None:
                game.cmd_gate(t, [(r, c)])

    elif action == "reset":
        board.reset()
        game.status = GameStatus.ONGOING  # ensure play resumes
        log.info(f"ACTION sid={sid} reset -> status={game.status.name}")  # DEBUG

    elif action == "new_same":
        board, game = build_board_and_game(cfg["rows"], cfg["cols"], cfg["bombs"], cfg["ent_level"],
                                           cfg["win"], cfg["moves"])
        GAMES[sid]["board"] = board
        GAMES[sid]["game"] = game
        log.info(f"ACTION sid={sid} new_same created")  # DEBUG

    elif action == "new_rules":
        log.info(f"ACTION sid={sid} new_rules -> redirect /setup")  # DEBUG
        return RedirectResponse("/setup", status_code=303)

    elif action == "set_tool" and tool:
        request.session["tool"] = tool.upper()
        log.info(f"ACTION sid={sid} set_tool={request.session['tool']}")  # DEBUG
        return RedirectResponse("/game", status_code=303)

    elif action == "toggle_theme":
        request.session["theme"] = "light" if request.session.get("theme", "dark") == "dark" else "dark"
        log.info(f"ACTION sid={sid} toggle_theme -> {request.session['theme']}")  # DEBUG

    log.info(f"POST /game sid={sid} status_after={game.status.name}")  # DEBUG
    return RedirectResponse("/game", status_code=303)
