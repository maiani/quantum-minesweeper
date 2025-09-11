# qminesweeper/webapp.py
from __future__ import annotations
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4

from qminesweeper.board import QMineSweeperBoard, CellState
from qminesweeper.game import QMineSweeperGame, GameConfig, WinCondition, MoveSet, GameStatus, MoveType
from qminesweeper.stim_backend import StimBackend  # default backend

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change-me-in-prod")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# per-session games
GAMES: dict[str, dict] = {}

def get_sid(request: Request) -> str:
    sid = request.session.get("sid")
    if not sid:
        sid = str(uuid4())
        request.session["sid"] = sid
    return sid

def clue_color(val: float) -> str:
    v = max(0.0, min(val / 8.0, 1.0))
    r = int(255 * v)
    g = int(255 * (1.0 - v))
    return f"rgb({r},{g},0)"

def build_board_and_game(rows:int, cols:int, bombs:int, ent_level:int,
                         basis:str, flood:bool,
                         win:WinCondition, moves:MoveSet):
    board = QMineSweeperBoard(rows, cols, backend=StimBackend(), flood_fill=flood)
    if ent_level == 0:
        board.span_classical_bombs(bombs)
    else:
        board.span_random_stabilizer_bombs(bombs, level=ent_level)
    board.set_clue_basis(basis)
    game = QMineSweeperGame(board, GameConfig(win_condition=win, move_set=moves))
    return board, game

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
    return templates.TemplateResponse("setup.html", {"request": request})

@app.post("/setup", name="setup_post")
async def setup_post(
    request: Request,
    # Legacy fields (from existing template)
    mode: Optional[int] = Form(None),
    rows: int = Form(...),
    cols: int = Form(...),
    bombs: int = Form(...),
    ent_level: int = Form(...),
    # Advanced fields (future template)
    win_condition: Optional[str] = Form(None),   # "identify" | "clear"
    move_set: Optional[str] = Form(None),        # "classic" | "one" | "clifford"
    basis: Optional[str] = Form("Z"),
    flood: Optional[str] = Form("on"),
):
    sid = get_sid(request)

    # Map legacy mode to rules
    if win_condition:
        win = WinCondition.CLEAR if win_condition.lower() == "clear" else WinCondition.IDENTIFY
    else:
        if mode == 3:
            win = WinCondition.CLEAR
        else:
            win = WinCondition.IDENTIFY

    if move_set:
        mv = {"classic": MoveSet.CLASSIC, "one": MoveSet.ONE_QUBIT, "clifford": MoveSet.TWO_QUBIT}.get(move_set.lower(), MoveSet.TWO_QUBIT)
    else:
        mv = MoveSet.CLASSIC if mode == 1 else MoveSet.TWO_QUBIT

    basis = (basis or "Z").upper()
    if basis not in ("X","Y","Z"):
        basis = "Z"
    flood_on = (flood != "off")

    board, game = build_board_and_game(rows, cols, bombs, ent_level, basis, flood_on, win, mv)

    GAMES[sid] = {
        "board": board,
        "game": game,
        "config": {"rows": rows, "cols": cols, "bombs": bombs, "ent_level": ent_level,
                   "win": win, "moves": mv, "basis": basis, "flood": flood_on},
    }
    request.session.setdefault("tool", "M")
    request.session.setdefault("basis", basis)
    request.session.setdefault("theme", "dark")
    return RedirectResponse("/game", status_code=303)

@app.get("/game", response_class=HTMLResponse, name="game_get")
async def game_get(request: Request):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]

    # tools available
    tools = ["M", "P", "X", "Y", "Z", "H", "S", "SDG", "SX", "SXDG", "SY", "SYDG", "CX", "CY", "CZ", "SWAP"]

    # build grid
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
            "current_basis": board.clue_basis,
            "theme": request.session.get("theme", "dark"),
        },
    )

@app.post("/game", name="game_post")
async def game_post(request: Request, action: str = Form(...), r: int = Form(None), c: int = Form(None),
                    r2: int = Form(None), c2: int = Form(None), tool: str = Form(None), basis: str = Form(None)):
    sid = get_sid(request)
    if sid not in GAMES:
        return RedirectResponse("/setup")

    board: QMineSweeperBoard = GAMES[sid]["board"]
    game: QMineSweeperGame = GAMES[sid]["game"]
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
        t = request.session.get("tool", "M").upper()
        if t in ("CX","CY","CZ","SWAP"):
            game.cmd_gate(t, [(r, c), (r2, c2)])
        elif t == "P":
            game.cmd_toggle_pin(r, c)
        else:
            game.cmd_measure(r, c)

    elif action == "reset":
        board.reset()

    elif action == "new_same":
        board, game = build_board_and_game(cfg["rows"], cfg["cols"], cfg["bombs"], cfg["ent_level"],
                                           cfg["basis"], cfg["flood"], cfg["win"], cfg["moves"])
        GAMES[sid]["board"] = board
        GAMES[sid]["game"] = game

    elif action == "new_rules":
        return RedirectResponse("/setup")

    elif action == "set_tool" and tool:
        request.session["tool"] = tool

    elif action == "set_basis" and basis:
        basis = basis.upper()
        if basis in ("X","Y","Z"):
            board.set_clue_basis(basis)
            request.session["basis"] = basis

    elif action == "toggle_theme":
        request.session["theme"] = "light" if request.session.get("theme", "dark") == "dark" else "dark"

    return RedirectResponse("/game", status_code=303)
