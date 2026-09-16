"""`make robinhood-auth`: run the one-time browser consent on a desktop and
persist the refresh token where the worker container will find it."""

from __future__ import annotations

from src.gateway.adapters.mcp_client import McpReadClient
from src.gateway.adapters.oauth_browser import BrowserConsent
from src.gateway.adapters.robinhood import settings_from_env


def main() -> None:
    url, path = settings_from_env()
    client = McpReadClient(url, path, consent=BrowserConsent())
    try:
        payload = client.call("get_equity_quotes", {"symbols": ["AAPL"]})
        results = (payload.get("data") or {}).get("results") or []
        status = "ok" if results else "returned no results"
        print(f"[robinhood-auth] token stored at {path}; quote check {status}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
