# qminesweeper/auth.py
from __future__ import annotations
import os, base64, secrets
from typing import Iterable, Optional, Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class BasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Auth. Excludes /health by default."""
    def __init__(self, app, username: Optional[str]=None, password: Optional[str]=None,
                 realm: str="Restricted", exclude_paths: Optional[Iterable[str]]=None):
        super().__init__(app)
        self.username = username or os.getenv("DEMO_USER", "demo")
        self.password = password or os.getenv("DEMO_PASS", "demo123")
        self.realm = realm
        raw = list(exclude_paths or ["/health"])
        self._exact: Set[str] = {p for p in raw if not p.endswith("*")}
        self._prefixes = tuple(p[:-1] for p in raw if p.endswith("*"))

    def _is_excluded(self, path: str) -> bool:
        return path in self._exact or any(path.startswith(pref) for pref in self._prefixes)

    async def dispatch(self, request, call_next):
        if self._is_excluded(request.url.path):
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return Response(status_code=401, headers={"WWW-Authenticate": f'Basic realm="{self.realm}"'})
        try:
            user_pass = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
            username, password = user_pass.split(":", 1)
        except Exception:
            return Response(status_code=401, headers={"WWW-Authenticate": f'Basic realm="{self.realm}"'})
        if not (secrets.compare_digest(username, self.username) and secrets.compare_digest(password, self.password)):
            return Response(status_code=401, headers={"WWW-Authenticate": f'Basic realm="{self.realm}"'})
        return await call_next(request)

def enable_basic_auth(app, **kwargs) -> None:
    app.add_middleware(BasicAuthMiddleware, **kwargs)
