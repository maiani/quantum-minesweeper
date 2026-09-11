"""Typed configuration and dashboard-ownership boundaries."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qminesweeper.settings import Settings


@pytest.mark.parametrize("field,value", [("BACKEND", "other"), ("RESET_POLICY", "sometimes")])
def test_closed_setting_vocabularies_are_validated(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_admin_values_exclude_operational_configuration():
    values = Settings(_env_file=None).admin_values()

    assert "ENABLE_ENTANGLEMENT_PROBES" in values
    assert "BACKEND" not in values
    assert "ADMIN_PASS" not in values
    assert "BROWSER_DIST_DIR" not in values


def test_persisted_admin_values_are_validated_atomically():
    settings = Settings(_env_file=None, ENABLE_HELP=True, RESET_POLICY="sandbox")

    with pytest.raises(ValidationError):
        settings.apply_admin_values({"ENABLE_HELP": False, "RESET_POLICY": "invalid"})

    assert settings.ENABLE_HELP is True
    assert settings.RESET_POLICY == "sandbox"


def test_one_product_snapshot_drives_both_consumer_shapes():
    product = Settings(
        _env_file=None,
        ENABLE_SURVEY=True,
        SURVEY_URL="https://example.test/survey",
        RESET_POLICY="never",
    ).product_config()

    features = product.template_features(browser_app_available=False)
    game_config = product.game_config()
    assert features["ENABLE_SURVEY"] is game_config["enable_survey"] is True
    assert features["SURVEY_URL"] == game_config["survey_url"]
    assert features["RESET_POLICY"] == game_config["reset_policy"] == "never"
