from __future__ import annotations

import base64
import secrets


class BasicAuthMiddleware:
    """ASGI middleware that enforces HTTP Basic Authentication.

    Protects HTTP and WebSocket connections. ASGI lifespan events pass through
    unconditionally. Credentials are compared in constant time to resist
    timing attacks.

    Usage with Starlette::

        app.add_middleware(BasicAuthMiddleware, username="user", password="secret")
    """

    def __init__(self, app, username: str, password: str) -> None:
        self.app = app
        self._username = username
        self._password = password

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        if not self._authorized(dict(scope.get("headers", []))):
            if scope["type"] == "http":
                body = b"Unauthorized"
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"www-authenticate", b'Basic realm="wiki-mcp"'),
                            (b"content-type", b"text/plain; charset=utf-8"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
            else:
                await send({"type": "websocket.close", "code": 1008})
            return

        await self.app(scope, receive, send)

    def _authorized(self, headers: dict[bytes, bytes]) -> bool:
        auth = headers.get(b"authorization", b"")
        if not auth.lower().startswith(b"basic "):
            return False
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            username, _, password = decoded.partition(":")
        except Exception:
            return False
        return secrets.compare_digest(username, self._username) and secrets.compare_digest(
            password, self._password
        )
