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
        if scope.get("type") == "http" and scope.get("path", "").startswith("/__debug"):
            import json
            body = json.dumps({"build": "debug-2", "path": scope.get("path"), "root_path": scope.get("root_path"),
                               "query": scope.get("query_string", b"").decode("latin-1"),
                               "headers": {k.decode(): v.decode() for k, v in scope.get("headers", [])
                                           if k.decode().startswith(("x-vercel", "x-forwarded", "x-matched", "host"))}}).encode()
            await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})
            return
        # strip a "/api/index" prefix if the runtime passes the function path instead of the original one
        if scope.get("type") == "http" and scope.get("path", "").startswith("/api/index"):
            rest = scope["path"][len("/api/index"):] or "/"
            scope = dict(scope, path=rest, raw_path=rest.encode("utf-8"))
        await self.inner(scope, receive, send)


app = _RestorePath(_fastapi)
