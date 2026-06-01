# tests/test_webapp_logic.py
"""
Logic-level tests for the web layer that don't need an HTTP client:
setup-parameter validation and the signed admin-session cookie.

(conftest.py sets QMS_ENABLE_AUTH=0 and a known QMS_ADMIN_PASS before import.)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from qminesweeper.webapp import (
    ADMIN_COOKIE,
    MAX_DIM,
    MAX_QUBITS,
    _admin_serializer,
    admin_authed,
    admin_enabled,
    validate_setup_params,
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
