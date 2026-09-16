"""Synchronous wrapper around one MCP streamable-HTTP session, restricted to
READ_TOOLS. The session lives on a background event loop so the rest of the
system (SQLAlchemy, APScheduler) can stay synchronous.

The OAuth token is the only credential in the system. It is read from and
written to the file at the path this module is given, never logged, and
never returned to callers.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Final

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

from src.gateway.adapters.oauth_browser import BrowserConsent
from src.gateway.allowlist import CapabilityError

READ_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "get_equity_quotes",
        "get_option_chains",
        "get_option_instruments",
        "get_option_quotes",
        "get_equity_historicals",
        "get_earnings_results",
        "get_equity_news",
    }
)

CLIENT_NAME = "Options Research Agent (read-only)"


class AuthRequired(RuntimeError):
    pass


class McpToolError(RuntimeError):
    pass


class FileTokenStorage(TokenStorage):
    def __init__(self, path: Path) -> None:
        self._path = path

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        loaded = json.loads(self._path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}

    def _save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data), encoding="utf-8")
        with contextlib.suppress(OSError):
            self._path.chmod(0o600)

    def has_tokens(self) -> bool:
        return "tokens" in self._load()

    async def get_tokens(self) -> OAuthToken | None:
        raw = self._load().get("tokens")
        return OAuthToken.model_validate(raw) if raw else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = self._load()
        data["tokens"] = tokens.model_dump(mode="json")
        self._save(data)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = self._load().get("client_info")
        return OAuthClientInformationFull.model_validate(raw) if raw else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        data = self._load()
        data["client_info"] = client_info.model_dump(mode="json")
        self._save(data)


class McpReadClient:
    def __init__(
        self,
        server_url: str,
        token_path: Path,
        consent: BrowserConsent | None = None,
        call_timeout: float = 90.0,
    ) -> None:
        self._server_url = server_url
        self._storage = FileTokenStorage(token_path)
        self._token_path = token_path
        self._consent = consent
        self._call_timeout = call_timeout
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="mcp-read-client", daemon=True
        )
        self._session: ClientSession | None = None
        self._stop: asyncio.Event | None = None
        self._runner: Future[None] | None = None

    def _provider(self) -> OAuthClientProvider:
        redirect: Callable[[str], Awaitable[None]]
        callback: Callable[[], Awaitable[AuthorizationCodeResult]]
        if self._consent is not None:
            redirect_uri = self._consent.redirect_uri
            redirect = self._consent.redirect
            callback = self._consent.callback
        else:
            redirect_uri = "http://localhost:3030/callback"
            message = (
                f"No usable Robinhood token at {self._token_path}. "
                "Run `make robinhood-auth` on a desktop with a browser first."
            )

            async def headless_redirect(_url: str) -> None:
                raise AuthRequired(message)

            async def headless_callback() -> AuthorizationCodeResult:
                raise AuthRequired(message)

            redirect = headless_redirect
            callback = headless_callback

        metadata = OAuthClientMetadata.model_validate(
            {
                "client_name": CLIENT_NAME,
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
            }
        )
        return OAuthClientProvider(
            server_url=self._server_url,
            client_metadata=metadata,
            storage=self._storage,
            redirect_handler=redirect,
            callback_handler=callback,
        )

    async def _run_session(self, ready: threading.Event) -> None:
        self._stop = asyncio.Event()
        async with AsyncExitStack() as stack:
            http = await stack.enter_async_context(httpx2.AsyncClient(auth=self._provider()))
            # Robinhood answers the SDK's session DELETE with 400; skip it.
            read, write = await stack.enter_async_context(
                streamable_http_client(
                    url=self._server_url, http_client=http, terminate_on_close=False
                )
            )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._session = session
            ready.set()
            await self._stop.wait()
        self._session = None

    def _ensure_started(self) -> None:
        if self._session is not None:
            return
        if not self._thread.is_alive():
            self._thread.start()
        ready = threading.Event()
        self._runner = asyncio.run_coroutine_threadsafe(self._run_session(ready), self._loop)
        while not ready.wait(0.1):
            if self._runner.done():
                self._runner.result()
                raise RuntimeError("MCP session ended before it became ready")

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool not in READ_TOOLS:
            raise CapabilityError(tool)
        self._ensure_started()
        assert self._session is not None
        future = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(tool, arguments, read_timeout_seconds=self._call_timeout),
            self._loop,
        )
        return _parse(tool, future.result(timeout=self._call_timeout + 5))

    def close(self) -> None:
        if self._runner is not None and self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
            self._runner.result(timeout=30)
            self._runner = None
        if self._thread.is_alive():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)

    def __enter__(self) -> McpReadClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _parse(tool: str, result: object) -> dict[str, Any]:
    content = getattr(result, "content", None) or []
    texts = [c.text for c in content if getattr(c, "type", "") == "text"]
    if getattr(result, "is_error", False):
        raise McpToolError(f"{tool}: {' '.join(texts)[:500]}")
    if not texts:
        raise McpToolError(f"{tool}: empty response")
    payload = json.loads(texts[0])
    if not isinstance(payload, dict):
        raise McpToolError(f"{tool}: unexpected response shape")
    return payload
