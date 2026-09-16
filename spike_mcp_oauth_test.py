#!/usr/bin/env python3
"""Stage 0a spike: can a plain, non-interactive Python script authenticate
to a remote MCP server (Robinhood's Trading MCP) and call a read tool,
without riding on an existing Claude Code/Desktop session?

Usage:
    pip install mcp httpx
    set MCP_URL=https://agent.robinhood.com/mcp/trading   (PowerShell: $env:MCP_URL = "...")
    python spike_mcp_oauth_test.py

If the server requires OAuth, this opens your default browser once for
consent and spins up a localhost callback server to catch the redirect.
Tokens are kept in memory only (not persisted to disk) — the point of
this spike is to observe whether the flow completes at all outside an
agent platform, not to build a keeper for the token yet.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx2
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

CALLBACK_PORT = 3030


class InMemoryTokenStorage(TokenStorage):
    def __init__(self) -> None:
        self._tokens: OAuthToken | None = None
        self._client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._tokens = tokens
        print(
            f"[spike] received token, expires_in={getattr(tokens, 'expires_in', 'unknown')}, "
            f"has_refresh_token={bool(getattr(tokens, 'refresh_token', None))}, "
            f"token_type={getattr(tokens, 'token_type', 'unknown')}, "
            f"scope={getattr(tokens, 'scope', 'unknown')}"
        )

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._client_info = client_info


class _CallbackState:
    def __init__(self) -> None:
        self.code: str | None = None
        self.state: str | None = None
        self.error: str | None = None


def _make_handler(state: _CallbackState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if "code" in params:
                state.code = params["code"][0]
                state.state = params.get("state", [None])[0]
                body = b"<html><body>Authorized. You can close this tab.</body></html>"
                self.send_response(200)
            else:
                state.error = params.get("error", ["unknown_error"])[0]
                body = f"<html><body>Auth failed: {state.error}</body></html>".encode()
                self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    return Handler


async def main() -> None:
    server_url = os.environ.get("MCP_URL")
    if not server_url:
        raise SystemExit("Set MCP_URL to the remote MCP server endpoint before running.")

    callback_state = _CallbackState()
    httpd = HTTPServer(("localhost", CALLBACK_PORT), _make_handler(callback_state))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"[spike] callback server listening on http://localhost:{CALLBACK_PORT}")

    async def redirect_handler(authorization_url: str) -> None:
        print(f"[spike] opening browser for consent: {authorization_url}")
        webbrowser.open(authorization_url)

    async def callback_handler() -> AuthorizationCodeResult:
        print("[spike] waiting up to 120s for OAuth redirect...")
        start = time.time()
        while time.time() - start < 120:
            if callback_state.code:
                return AuthorizationCodeResult(
                    code=callback_state.code, state=callback_state.state, iss=None
                )
            if callback_state.error:
                raise RuntimeError(f"OAuth error: {callback_state.error}")
            time.sleep(0.2)
        raise TimeoutError("Timed out waiting for OAuth redirect")

    oauth_auth = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata.model_validate(
            {
                "client_name": "Options Research Agent - Stage 0a spike",
                "redirect_uris": [f"http://localhost:{CALLBACK_PORT}/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
            }
        ),
        storage=InMemoryTokenStorage(),
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )

    try:
        print(f"[spike] connecting to {server_url} ...")
        async with httpx2.AsyncClient(auth=oauth_auth) as client:
            async with streamable_http_client(url=server_url, http_client=client) as (
                read_stream,
                write_stream,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    print("[spike] session initialized")

                    tools = await session.list_tools()
                    print(f"[spike] {len(tools.tools)} tools available:")
                    for tool in tools.tools:
                        print(f"  - {tool.name}")

                    if not any(t.name == "get_equity_quotes" for t in tools.tools):
                        print("[spike] WARNING: get_equity_quotes not in tool list, trying anyway")

                    result = await session.call_tool("get_equity_quotes", {"symbols": ["AAPL"]})
                    print("[spike] get_equity_quotes result:")
                    for content in result.content:
                        print(getattr(content, "text", content))
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
