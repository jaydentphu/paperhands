"""One-time interactive OAuth consent, for a desktop with a browser.

Used only by `make robinhood-auth`. The worker container never has a
browser; it relies on the refresh token this flow persists.
"""

from __future__ import annotations

import asyncio
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from mcp.shared.auth import AuthorizationCodeResult

CALLBACK_PORT = 3030


class BrowserConsent:
    def __init__(self, port: int = CALLBACK_PORT, timeout: float = 300.0) -> None:
        self._port = port
        self._timeout = timeout
        self._code: str | None = None
        self._state: str | None = None
        self._error: str | None = None
        self._httpd: HTTPServer | None = None

    @property
    def redirect_uri(self) -> str:
        return f"http://localhost:{self._port}/callback"

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        consent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                params = parse_qs(urlparse(self.path).query)
                codes = params.get("code")
                if codes:
                    consent._code = codes[0]
                    states = params.get("state")
                    consent._state = states[0] if states else None
                    body = b"<html><body>Authorized. You can close this tab.</body></html>"
                    self.send_response(200)
                else:
                    errors = params.get("error")
                    consent._error = errors[0] if errors else "unknown_error"
                    failure = f"<html><body>Authorization failed: {consent._error}</body></html>"
                    body = failure.encode()
                    self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass

        return Handler

    async def redirect(self, authorization_url: str) -> None:
        self._httpd = HTTPServer(("localhost", self._port), self._handler())
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        print(f"[robinhood-auth] opening browser for consent: {authorization_url}")
        webbrowser.open(authorization_url)

    async def callback(self) -> AuthorizationCodeResult:
        start = time.monotonic()
        try:
            while time.monotonic() - start < self._timeout:
                if self._code:
                    return AuthorizationCodeResult(code=self._code, state=self._state, iss=None)
                if self._error:
                    raise RuntimeError(f"OAuth consent failed: {self._error}")
                await asyncio.sleep(0.2)
            raise TimeoutError("Timed out waiting for the OAuth redirect")
        finally:
            if self._httpd is not None:
                self._httpd.shutdown()
