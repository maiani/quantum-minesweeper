# qminesweeper/auth.py
from __future__ import annotations
import os
import base64
import secrets
from typing import Iterable, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

ENABLE_AUTH_ENV = "QMS_ENABLE_AUTH"
USERNAME_ENV = "QMS_USER"
PASSWORD_ENV = "QMS_PASS"

# ---------- middleware ----------

class BasicAuthMiddleware(BaseHTTPMiddleware):
    """
    HTTP Basic Auth middleware.

    - Excluded paths support exact matches ("/health") and prefix patterns (".../*").
    - Raises RuntimeError at startup if credentials are missing while auth is enabled.
    """

    def __init__(
        self,
        app,
        username: Optional[str] = None,
        password: Optional[str] = None,
        realm: str = "Restricted",
        exclude_paths: Optional[Iterable[str]] = None,
    ):
        super().__init__(app)

        user_str = (username or os.getenv(USERNAME_ENV) or "").strip()
        pass_str = (password or os.getenv(PASSWORD_ENV) or "").strip()

        if not user_str or not pass_str:
            raise RuntimeError(
                "BasicAuthMiddleware: credentials not configured. "
                "Set QMS_USER and QMS_PASS (env) or pass username/password."
            )

        # store as bytes for constant-time comparisons (and to satisfy type checkers)
        self._user_b = user_str.encode("utf-8")
        self._pass_b = pass_str.encode("utf-8")

        self.realm = realm

        raw = list(exclude_paths or ["/health"])
        self._exact: Set[str] = {p for p in raw if not p.endswith("*")}
        self._prefixes = tuple(p[:-1] for p in raw if p.endswith("*"))

    def _is_excluded(self, path: str) -> bool:
        return path in self._exact or any(path.startswith(pref) for pref in self._prefixes)

    def _challenge(self) -> Response:
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": f'Basic realm="{self.realm}"'},
        )

    async def dispatch(self, request, call_next):
        path = request.url.path
        if self._is_excluded(path):
            return await call_next(request)

        # allow either header casing
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return self._challenge()

        try:
            b64 = auth.split(" ", 1)[1].strip()
            raw = base64.b64decode(b64, validate=True).decode("utf-8")
            username, password = raw.split(":", 1)
        except Exception:
            return self._challenge()

        if not (
            secrets.compare_digest(username.encode("utf-8"), self._user_b)
            and secrets.compare_digest(password.encode("utf-8"), self._pass_b)
        ):
            return self._challenge()

        return await call_next(request)

# ---------- setup API ----------

def enable_basic_auth(
    app,
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
    realm: str = "Quantum Minesweeper",
    exclude_paths: Optional[Iterable[str]] = None,
) -> bool:
    """
    Conditionally enable Basic Auth on `app`.

    Enabling rules:
      - If QMS_ENABLE_AUTH is set to 1
      - If QMS_ENABLE_AUTH is NOT set: enable iff both credentials are present
        (from args or QMS_USER/QMS_PASS env). Otherwise disabled.

    If enabled but credentials are missing, raises RuntimeError.

    Returns:
      bool: True if middleware was added; False if auth is disabled.
    """
    env_val = os.getenv(ENABLE_AUTH_ENV)
    if env_val is not None:
        enabled = env_val.strip().lower() == "1"
    else:
        # auto-enable only if creds exist
        u = (username or os.getenv(USERNAME_ENV) or "").strip()
        p = (password or os.getenv(PASSWORD_ENV) or "").strip()
        enabled = bool(u and p)

    if not enabled:
        return False

    # Will raise with a clear error if creds are missing:
    app.add_middleware(
        BasicAuthMiddleware,
        username=username,
        password=password,
        realm=realm,
        exclude_paths=exclude_paths or ["/health", "/static/*"],
    )
    return True
