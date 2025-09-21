# qminesweeper/ayth.py
from __future__ import annotations

import base64
import secrets
from typing import Iterable, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from qminesweeper.settings import get_settings

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
        *,
        username: str,
        password: str,
        realm: str = "Restricted",
        exclude_paths: Optional[Iterable[str]] = None,
    ):
        super().__init__(app)

        user_str = (username or "").strip()
        pass_str = (password or "").strip()
        if not user_str or not pass_str:
            raise RuntimeError(
                "BasicAuthMiddleware: credentials not configured. Provide username/password (from settings or args)."
            )

        # store as bytes for constant-time comparisons
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
    Enable Basic Auth if QMS settings say so.

    Rules:
      - If settings.ENABLE_AUTH is False: do nothing.
      - If True: require username/password (from args or settings.USER/PASS) else raise.
    """
    settings = get_settings()

    if not settings.ENABLE_AUTH:
        return False

    u = (username or settings.USER or "").strip()
    p = (password or settings.PASS or "").strip()
    if not u or not p:
        raise RuntimeError(
            "Auth is enabled but credentials are missing. Set QMS_USER / QMS_PASS or pass username/password."
        )

    app.add_middleware(
        BasicAuthMiddleware,
        username=u,
        password=p,
        realm=realm,
        exclude_paths=exclude_paths or ["/health", "/static/*"],
    )
    return True
