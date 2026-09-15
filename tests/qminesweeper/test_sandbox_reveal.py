"""Read-only Sandbox reveal contract and entanglement-link semantics."""

from __future__ import annotations

import asyncio
import copy
import json

import pytest

from qminesweeper import server
from qminesweeper.browser import BrowserSession
from qminesweeper.chppy_backend import ChppyBackend
from qminesweeper.engine import build_game, reveal_board
from qminesweeper.game import MoveSet, WinCondition
from qminesweeper.qiskit_backend import QiskitBackend
from qminesweeper.stim_backend import StimBackend


def _sandbox(cols: int = 3) -> BrowserSession:
    session = BrowserSession()
    session.setup(1, cols, 0, 0, "sandbox", "two_extended", True, True)
    return session


def test_reveal_distinguishes_product_superposition_and_entangled_networks():
    product = _sandbox(2)
    product.move("H 1,1")
    product_result = product.reveal()
    assert product_result["cells"][0] == pytest.approx({"mine_probability": 0.5, "entropy": 0.0})
    assert product_result["entanglement_links"] == []
    assert product_result["links_complete"] is True

    bell = _sandbox(2)
    bell.move("H 1,1")
    bell.move("CX 1,1 1,2")
    bell_result = bell.reveal()
    assert [cell["mine_probability"] for cell in bell_result["cells"]] == pytest.approx([0.5, 0.5])
    assert [cell["entropy"] for cell in bell_result["cells"]] == pytest.approx([1.0, 1.0])
    assert bell_result["entanglement_links"] == [
        {"cells": [0, 1], "mutual_information": pytest.approx(2.0)}
    ]

    ghz = _sandbox(3)
    ghz.move("H 1,1")
    ghz.move("CX 1,1 1,2")
    ghz.move("CX 1,1 1,3")
    ghz_result = ghz.reveal()
    assert [cell["entropy"] for cell in ghz_result["cells"]] == pytest.approx([1.0, 1.0, 1.0])
    assert ghz_result["entanglement_links"] == [
        {"cells": [0, 1], "mutual_information": pytest.approx(1.0)},
        {"cells": [0, 2], "mutual_information": pytest.approx(1.0)},
        {"cells": [1, 2], "mutual_information": pytest.approx(1.0)},
    ]


@pytest.mark.parametrize("backend", [ChppyBackend(), StimBackend(), QiskitBackend()])
def test_reveal_network_has_backend_parity(backend):
    board, game = build_game(
        backend, 1, 3, 0, 0, WinCondition.SANDBOX, MoveSet.TWO_QUBIT_EXTENDED, True, True
    )
    board.apply_gate("H", [(0, 0)])
    board.apply_gate("CX", [(0, 0), (0, 1)])
    board.apply_gate("CX", [(0, 0), (0, 2)])

    result = reveal_board(board, game)

    assert [cell["mine_probability"] for cell in result["cells"]] == pytest.approx([0.5, 0.5, 0.5])
    assert [link["cells"] for link in result["entanglement_links"]] == [[0, 1], [0, 2], [1, 2]]
    assert [link["mutual_information"] for link in result["entanglement_links"]] == pytest.approx([1.0, 1.0, 1.0])


def test_large_dense_reveal_network_is_responsibly_simplified():
    board, game = build_game(
        ChppyBackend(), 10, 10, 0, 0, WinCondition.SANDBOX, MoveSet.TWO_QUBIT_EXTENDED, True, True
    )
    board.apply_gate("H", [(0, 0)])
    for index in range(1, board.n):
        board.apply_gate("CX", [(0, 0), (index // board.cols, index % board.cols)])

    result = reveal_board(board, game)

    assert all(cell["entropy"] == pytest.approx(1.0) for cell in result["cells"])
    assert len(result["entanglement_links"]) == 512
    assert result["links_complete"] is False


def test_reveal_is_sandbox_only_and_does_not_mutate_browser_state():
    session = _sandbox(2)
    session.move("H 1,1")
    before = copy.deepcopy(session.export_save())
    session.reveal()
    assert session.export_save() == before

    identify = BrowserSession()
    identify.setup(1, 2, 0, 0, "identify", "two_extended", True, True)
    with pytest.raises(ValueError, match="Sandbox"):
        identify.reveal()


async def _server_reveal_contract():
    gid = "reveal-test"
    reveal_was_enabled = server.settings.ENABLE_SANDBOX_REVEAL
    board, game = server.build_board_and_game(
        1, 2, 0, 0, server.WinCondition.SANDBOX, server.MoveSet.TWO_QUBIT_EXTENDED, True, True
    )
    board.apply_gate("H", [(0, 0)])
    board.apply_gate("CX", [(0, 0), (0, 1)])
    server.GAMES[gid] = {"board": board, "game": game, "config": {}, "last_seen": None}
    try:
        response = await server.reveal_post(gid)
        assert response.status_code == 200
        result = json.loads(response.body)
        assert result["entanglement_links"] == [
            {"cells": [0, 1], "mutual_information": pytest.approx(2.0)}
        ]

        expired = await server.reveal_post("missing")
        assert expired.status_code == 404
        assert json.loads(expired.body) == {"error": "game_not_found", "redirect": "/setup"}

        other_board, other_game = server.build_board_and_game(
            1, 2, 0, 0, server.WinCondition.IDENTIFY, server.MoveSet.TWO_QUBIT_EXTENDED, True, True
        )
        server.GAMES["not-sandbox"] = {
            "board": other_board, "game": other_game, "config": {}, "last_seen": None,
        }
        denied = await server.reveal_post("not-sandbox")
        assert denied.status_code == 400
        assert "Sandbox" in json.loads(denied.body)["error"]

        server.settings.ENABLE_SANDBOX_REVEAL = False
        disabled = await server.reveal_post(gid)
        assert disabled.status_code == 403
        assert "disabled" in json.loads(disabled.body)["error"]
    finally:
        server.settings.ENABLE_SANDBOX_REVEAL = reveal_was_enabled
        server.GAMES.pop(gid, None)
        server.GAMES.pop("not-sandbox", None)


def test_server_reveal_success_errors_and_expiry():
    asyncio.run(_server_reveal_contract())


def test_reveal_ui_is_sandbox_scoped_and_documents_its_visual_semantics():
    source = (server.STATIC_DIR / "scripts" / "render.js").read_text()
    css = (server.STATIC_DIR / "styles" / "game.css").read_text()
    help_visual = (server.STATIC_DIR / "help" / "reveal" / "visual.html").read_text()
    admin = (server.TEMPLATES_DIR / "admin_home.html").read_text()
    browser_shell = (server.BASE_DIR.parents[1] / "scripts" / "browser_index.html").read_text()
    browser_main = (server.STATIC_DIR / "scripts" / "browser-main.js").read_text()
    assert 'state.win_condition !== "SANDBOX"' in source
    assert "!_config.sandbox_reveal" in source
    assert '"help-id": "reveal"' in source
    assert "entanglement_links" in source
    assert "reveal-probability" not in source
    assert "reveal-bomb" in source
    assert ".board-revealed button.reveal-visible" in css
    assert ".entanglement-link" in css
    assert "isolation: isolate" in css
    assert "z-index: 10" in css
    assert ">0%<" not in help_visual
    assert ">50%<" not in help_visual
    assert ">100%<" not in help_visual
    assert 'name="ENABLE_SANDBOX_REVEAL"' in admin
    assert 'id="reveal-container"' in browser_shell
    assert '"reveal-container"' in browser_main
