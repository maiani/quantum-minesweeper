# qminesweeper/webapp.py
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4

from qminesweeper.quantum_board import QMineSweeperGame, GameMode, MoveType, CellState
from qminesweeper.stim_backend import StimBackend  # default backend

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-me-in-prod")

# --------------------------------------------------------------------
# Use paths relative to this file (qminesweeper/webapp.py)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
# --------------------------------------------------------------------

# per-session games
GAMES: dict[str, dict] = {}

def get_sid(request: Request) -> str:
    sid = request.session.get("sid")
    if not sid:
        sid = str(uuid4())
        request.session["sid"] = sid
    return sid

def make_board(mode: GameMode, rows: int, cols: int, n_bombs: int, ent_level: int) -> QMineSweeperGame:
    qb = QMineSweeperGame(rows, cols, mode, backend=StimBackend())
    if ent_level == 0:
        qb.span_classical_bombs(n_bombs)
    else:
        qb.span_random_stabilizer_bombs(n_bombs, level=ent_level)
    return qb

def clue_color(val: float) -> str:
    v = max(0.0, min(val / 8.0, 1.0))
    r = int(255 * v)
    g = int(255 * (1.0 - v))
    return f"rgb({r},{g},0)"

@app.get("/health")
def health():
    return PlainTextResponse("ok")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")
    return RedirectResponse("/game")

@app.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request):
    return templates.TemplateResponse("setup.html", {"request": request})

@app.post("/setup")
async def setup_post(
    request: Request,
    mode: int = Form(...),
    rows: int = Form(...),
    cols: int = Form(...),
    bombs: int = Form(...),
    ent_level: int = Form(...)
):
    sid = get_sid(request)
    mode_map = {1: GameMode.CLASSIC, 2: GameMode.QUANTUM_IDENTIFY, 3: GameMode.QUANTUM_CLEAR}
    qb = make_board(mode_map[mode], rows, cols, bombs, ent_level)
    GAMES[sid] = {
        "board": qb,
        "config": {"mode": mode_map[mode], "rows": rows, "cols": cols,
                   "bombs": bombs, "ent_level": ent_level},
    }
    request.session.setdefault("tool", "M")
    request.session.setdefault("basis", "Z")
    request.session.setdefault("theme", "dark")
    return RedirectResponse("/game", status_code=303)

@app.get("/game", response_class=HTMLResponse)
async def game_get(request: Request):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")

    qb: QMineSweeperGame = GAMES[sid]["board"]
    cfg = GAMES[sid]["config"]
    mode = cfg["mode"]

    # tools available
    tools = ["M", "P", "X", "Y", "Z", "H", "S", "SDG", "SX", "SXDG", "SY", "SYDG", "CX", "CY", "CZ", "SWAP"]

    # build grid
    grid = []
    for r in range(qb.rows):
        row = []
        for c in range(qb.cols):
            state = qb.exploration_state[r, c]
            cell = {"r": r, "c": c, "text": "", "style": ""}
            if state == CellState.UNEXPLORED:
                cell["text"] = "■"
                cell["style"] = "color:var(--tile-muted);"
            elif state == CellState.PINNED:
                cell["text"] = "⚑"
                cell["style"] = "color:var(--pin);"
            else:
                val = qb.get_clue(r, c)
                if val == 9.0:
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

    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "grid": grid,
            "rows": qb.rows,
            "cols": qb.cols,
            "status": qb.game_status.name,
            "tools": tools,
            "current_tool": request.session.get("tool", "M"),
            "current_basis": request.session.get("basis", "Z"),
            "theme": request.session.get("theme", "dark"),
        },
    )

@app.post("/game")
async def game_post(request: Request, action: str = Form(...), r: int = Form(None), c: int = Form(None),
                    r2: int = Form(None), c2: int = Form(None), tool: str = Form(None), basis: str = Form(None)):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")

    qb: QMineSweeperGame = GAMES[sid]["board"]
    cfg = GAMES[sid]["config"]

    cmd_map = {
        "M": MoveType.MEASURE, "P": MoveType.PIN_TOGGLE,
        "X": MoveType.X_GATE, "Y": MoveType.Y_GATE, "Z": MoveType.Z_GATE,
        "H": MoveType.H_GATE, "S": MoveType.S_GATE, "SDG": MoveType.SDG_GATE,
        "SX": MoveType.SX_GATE, "SXDG": MoveType.SXDG_GATE,
        "SY": MoveType.SY_GATE, "SYDG": MoveType.SYDG_GATE,
        "CX": MoveType.CX_GATE, "CY": MoveType.CY_GATE,
        "CZ": MoveType.CZ_GATE, "SWAP": MoveType.SWAP_GATE,
    }

    if action == "cell":
        t = request.session.get("tool", "M")
        move_type = cmd_map.get(t, MoveType.MEASURE)
        if move_type in (MoveType.CX_GATE, MoveType.CY_GATE, MoveType.CZ_GATE, MoveType.SWAP_GATE):
            qb.move(move_type, (r, c), (r2, c2))
        else:
            qb.move(move_type, (r, c))

    elif action == "reset":
        qb.reset_board()

    elif action == "new_same":
        GAMES[sid]["board"] = make_board(cfg["mode"], cfg["rows"], cfg["cols"], cfg["bombs"], cfg["ent_level"])

    elif action == "new_rules":
        return RedirectResponse("/setup")

    elif action == "set_tool" and tool:
        request.session["tool"] = tool

    elif action == "set_basis" and basis:
        qb.set_clue_basis(basis)
        request.session["basis"] = basis

    elif action == "toggle_theme":
        request.session["theme"] = "light" if request.session.get("theme", "dark") == "dark" else "dark"

    return RedirectResponse("/game", status_code=303)
