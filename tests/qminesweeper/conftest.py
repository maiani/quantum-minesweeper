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
from pathlib import Path
from tempfile import mkdtemp

os.environ.setdefault("QMS_ENABLE_AUTH", "0")
os.environ.setdefault("QMS_ADMIN_PASS", "test-admin-pass")
# Server imports create/migrate the SQLite schema. Never let a developer's .env
# send tests to a real local or mounted database; each pytest process gets an
# isolated disposable store before Settings or server modules are imported.
os.environ["QMS_DB_PATH"] = str(Path(mkdtemp(prefix="qms-pytest-")) / "qms.sqlite")

from qminesweeper.settings import get_settings  # noqa: E402

get_settings.cache_clear()
