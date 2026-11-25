"""Vercel entry point: exposes the FastAPI app.

vercel.json rewrites every URL to /api/index?__path=<original path>; this wrapper restores the original
path before FastAPI routes the request, so it works whatever path the runtime passes through.
"""
import sys, pathlib
from urllib.parse import parse_qsl, urlencode

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.main import app as _fastapi  # noqa: E402


class _RestorePath:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            qs = parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
            original = [v for k, v in qs if k == "__path"]
            if original:
                path = "/" + original[0].lstrip("/")
                scope = dict(scope, path=path, raw_path=path.encode("utf-8"),
                             query_string=urlencode([(k, v) for k, v in qs if k != "__path"]).encode("latin-1"))
        await self.inner(scope, receive, send)


app = _RestorePath(_fastapi)
