"""
Test configuration for the game suite.

This file belongs beside the game tests rather than at the tests/ root: a root
conftest would also apply to tests/chppy/, making the standalone library's test
run import this application. Keep game-wide fixtures here.

Set auth-related env BEFORE qminesweeper.server is imported by any test, so the
app module (which builds Basic Auth middleware at import time and reads
ADMIN_PASS) can be imported without real credentials. Disabling auth keeps the
import side-effect-free; a known ADMIN_PASS lets us exercise admin-session logic.
"""

import os

os.environ.setdefault("QMS_ENABLE_AUTH", "0")
os.environ.setdefault("QMS_ADMIN_PASS", "test-admin-pass")

from qminesweeper.settings import get_settings  # noqa: E402

get_settings.cache_clear()
