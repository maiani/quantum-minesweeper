# tests/test_server_logic.py
"""
Logic-level tests for the web layer that don't need an HTTP client:
setup-parameter validation and the signed admin-session cookie.

(conftest.py sets QMS_ENABLE_AUTH=0 and a known QMS_ADMIN_PASS before import.)
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from qminesweeper.engine import MAX_DIM, MAX_QUBITS, validate_setup_params
from qminesweeper.server import (
    ADMIN_COOKIE,
    _admin_serializer,
    admin_authed,
    admin_enabled,
    home,
    robots_txt,
    sitemap_xml,
    templates,
)


# ---------- setup validation ----------
def test_validate_setup_accepts_reasonable_params():
    validate_setup_params(rows=10, cols=10, mines=10, ent_level=1)
    validate_setup_params(rows=25, cols=15, mines=60, ent_level=4)  # largest UI preset


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(rows=0, cols=10, mines=1, ent_level=0),
        dict(rows=10, cols=0, mines=1, ent_level=0),
        dict(rows=MAX_DIM + 1, cols=10, mines=1, ent_level=0),
        dict(rows=100000, cols=100000, mines=1, ent_level=0),  # the OOM case
        dict(rows=10, cols=10, mines=101, ent_level=0),  # mines > cells
        dict(rows=10, cols=10, mines=-1, ent_level=0),
        dict(rows=10, cols=10, mines=1, ent_level=-1),
        dict(rows=10, cols=10, mines=1, ent_level=999),
    ],
)
def test_validate_setup_rejects_bad_params(kwargs):
    with pytest.raises(ValueError):
        validate_setup_params(**kwargs)


def test_max_qubits_guard():
    # Within per-dim limits but over the total-cell cap.
    assert MAX_DIM * MAX_DIM > MAX_QUBITS
    with pytest.raises(ValueError):
        validate_setup_params(rows=MAX_DIM, cols=MAX_DIM, mines=0, ent_level=0)


# ---------- admin session ----------
def _req(cookies: dict) -> SimpleNamespace:
    return SimpleNamespace(cookies=cookies)


def test_admin_enabled_when_pass_set():
    assert admin_enabled() is True  # conftest set QMS_ADMIN_PASS


def test_admin_authed_accepts_valid_token():
    token = _admin_serializer().dumps("ok")
    assert admin_authed(_req({ADMIN_COOKIE: token})) is True


def test_admin_authed_rejects_missing_and_tampered():
    assert admin_authed(_req({})) is False
    assert admin_authed(_req({ADMIN_COOKIE: "not-a-valid-token"})) is False


def test_admin_authed_rejects_token_signed_with_other_secret():
    from itsdangerous import URLSafeTimedSerializer

    forged = URLSafeTimedSerializer("a-different-secret", salt="qms-admin-session").dumps("ok")
    assert admin_authed(_req({ADMIN_COOKIE: forged})) is False


# ---------- public SEO URL shape ----------
def _home_request() -> SimpleNamespace:
    return SimpleNamespace(cookies={}, url=SimpleNamespace(scheme="http"))


def test_home_redirects_to_stable_setup_url():
    """Without the installable app, the server-rendered game is the landing."""
    resp = asyncio.run(home(_home_request()))

    assert resp.status_code == 307
    assert resp.headers["location"] == "/setup"


def test_home_lands_on_the_browser_app_when_it_is_offered(monkeypatch):
    """A deployment offering the app sends visitors there, so play runs in their browser."""
    from qminesweeper import server

    monkeypatch.setattr(server, "BROWSER_APP_AVAILABLE", True)
    monkeypatch.setattr(server.settings, "ENABLE_BROWSER_APP", True)

    resp = asyncio.run(home(_home_request()))

    assert resp.headers["location"] == "/app/"
    # 307, not 301: the target follows a runtime setting, and a cached permanent
    # redirect would keep sending visitors to /app/ after it was switched off.
    assert resp.status_code == 307


def test_home_stays_on_the_server_game_when_the_app_is_switched_off(monkeypatch):
    """The bundle may exist while the deployment chooses not to offer it."""
    from qminesweeper import server

    monkeypatch.setattr(server, "BROWSER_APP_AVAILABLE", True)
    monkeypatch.setattr(server.settings, "ENABLE_BROWSER_APP", False)

    assert asyncio.run(home(_home_request())).headers["location"] == "/setup"


def test_home_stays_on_the_server_game_when_no_bundle_exists(monkeypatch):
    """The switch cannot conjure a bundle, so it must not redirect to nothing."""
    from qminesweeper import server

    monkeypatch.setattr(server, "BROWSER_APP_AVAILABLE", False)
    monkeypatch.setattr(server.settings, "ENABLE_BROWSER_APP", True)

    assert asyncio.run(home(_home_request())).headers["location"] == "/setup"


def test_setup_uses_stable_public_links():
    html = templates.env.get_template("setup.html").render(game_id=None, error=None)

    assert 'action="/setup"' in html
    assert "/setup?game_id" not in html
    assert 'href="/about"' in html
    assert "/about?game_id" not in html


def test_header_renders_about_link():
    # The game now links to a clean /about (no game_id) — the about page's Back
    # button returns to the game via history, so no per-game URL is minted.
    html = templates.env.get_template("header.html").render(ABOUT_HREF="/about")

    assert 'href="/about"' in html


def test_about_without_game_id_links_to_setup():
    html = templates.env.get_template("about.html").render(game_id=None)

    assert 'href="/setup"' in html
    assert "/game?game_id" not in html


def test_about_has_back_button_without_minting_game_url():
    # About offers a single "Back" (history.back()) rather than a /game?game_id=
    # link, keeping /about a clean canonical page (no per-game crawl-trap URLs).
    html = templates.env.get_template("about.html").render(game_id="gid-1")

    assert "history.back()" in html
    assert "/game?game_id" not in html


def test_robots_txt_points_to_sitemap_and_skips_action_endpoints():
    resp = robots_txt()
    text = resp.body.decode()

    assert resp.media_type == "text/plain"
    assert "User-agent: *" in text
    assert "Disallow: /move" in text
    assert "Disallow: /admin/db_download" in text
    assert "Sitemap: http://127.0.0.1:8080/sitemap.xml" in text


def test_sitemap_lists_only_stable_public_pages():
    resp = sitemap_xml()
    text = resp.body.decode()

    assert resp.media_type == "application/xml"
    assert "<loc>http://127.0.0.1:8080/setup</loc>" in text
    assert "<loc>http://127.0.0.1:8080/about</loc>" in text
    assert "game_id" not in text
    assert "/admin" not in text


@pytest.mark.parametrize(
    ("template_name", "context"),
    [
        ("admin_login.html", {"error": None}),
        ("admin_home.html", {}),
        ("db_view.html", {"rows": [{"game_id": "gid-1", "status": "WIN", "prep_circuit": ""}]}),
    ],
)
def test_admin_pages_emit_noindex(template_name, context):
    html = templates.env.get_template(template_name).render(**context)

    assert '<meta name="robots" content="noindex, nofollow">' in html
