# ./src/flask-webapp.py
from __future__ import annotations
from flask import Flask, render_template, request, redirect, url_for, session, Response
from uuid import uuid4

from quantum_board import QMineSweeperGame, GameMode, MoveType, CellState
from qiskit_backend import QiskitBackend

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)
app.secret_key = "change-me-in-prod"

GAMES: dict[str, dict] = {}


def get_sid() -> str:
    if "sid" not in session:
        session["sid"] = str(uuid4())
        session.permanent = True
    return session["sid"]


def make_board(mode: GameMode, rows: int, cols: int, n_bombs: int, btype: int) -> QMineSweeperGame:
    qb = QMineSweeperGame(rows, cols, mode, backend=QiskitBackend())
    if btype == 1:
        qb.span_classical_bombs(n_bombs)
    else:
        qb.span_quantum_product_bombs(n_bombs)
    return qb


@app.get("/health")
def health():
    return Response("ok", status=200, mimetype="text/plain")

@app.route("/")
def home():
    sid = get_sid()
    if sid not in GAMES:
        return redirect(url_for("setup"))
    return redirect(url_for("game"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        mode_sel = int(request.form.get("mode", "1"))
        rows = int(request.form.get("rows", "5"))
        cols = int(request.form.get("cols", "5"))
        n_bombs = int(request.form.get("bombs", "5"))
        btype = int(request.form.get("btype", "1"))

        mode = {1: GameMode.CLASSIC, 2: GameMode.QUANTUM_IDENTIFY, 3: GameMode.QUANTUM_CLEAR}[mode_sel]
        qb = make_board(mode, rows, cols, n_bombs, btype)

        sid = get_sid()
        GAMES[sid] = {
            "board": qb,
            "config": {"mode": mode, "rows": rows, "cols": cols, "bombs": n_bombs, "btype": btype},
        }
        # defaults
        session.setdefault("tool", "M")
        session.setdefault("theme", "dark")
        return redirect(url_for("game"))

    return render_template("setup.html")


def clue_color(val: float) -> str:
    v = max(0.0, min(val / 8.0, 1.0))
    r = int(255 * v)
    g = int(255 * (1.0 - v))
    return f"rgb({r},{g},0)"


@app.route("/game", methods=["GET", "POST"])
def game():
    sid = get_sid()
    if sid not in GAMES:
        return redirect(url_for("setup"))

    qb: QMineSweeperGame = GAMES[sid]["board"]
    cfg = GAMES[sid]["config"]
    mode = cfg["mode"]

    # Tools depend on mode
    tools = ["M", "P"]
    if mode in (GameMode.QUANTUM_IDENTIFY, GameMode.QUANTUM_CLEAR):
        tools += ["X", "Y", "Z", "H", "S"]

    # Defaults in session
    current_tool = session.get("tool", "M")
    theme = session.get("theme", "dark")

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "cell":
            r = int(request.form["r"])
            c = int(request.form["c"])
            # Use the session-selected tool
            tool = session.get("tool", "M")
            cmd_map = {
                "M": MoveType.MEASURE, "P": MoveType.PIN_TOGGLE,
                "X": MoveType.X_GATE, "Y": MoveType.Y_GATE, "Z": MoveType.Z_GATE,
                "H": MoveType.H_GATE, "S": MoveType.S_GATE
            }
            move_type = cmd_map.get(tool, MoveType.MEASURE)
            qb.move(move_type, (r, c))

        elif action == "reset":
            qb.reset_board()

        elif action == "new_same":
            GAMES[sid]["board"] = make_board(cfg["mode"], cfg["rows"], cfg["cols"], cfg["bombs"], cfg["btype"])

        elif action == "new_rules":
            return redirect(url_for("setup"))

        elif action == "set_tool":
            t = request.form.get("tool", "M")
            if t in tools:
                session["tool"] = t

        elif action == "toggle_theme":
            session["theme"] = "light" if session.get("theme", "dark") == "dark" else "dark"

        return redirect(url_for("game"))

    # Build display model
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

    return render_template(
        "game.html",
        grid=grid, rows=qb.rows, cols=qb.cols,
        status=qb.game_status.name,
        tools=tools,
        current_tool=session.get("tool", "M"),
        theme=session.get("theme", "dark")
    )
