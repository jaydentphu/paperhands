"""Robinhood Trading MCP adapter.

Connection settings come from env here and nowhere else (CLAUDE.md rules 3
and 7). Only the read tools in mcp_client.READ_TOOLS are ever named.
"""

from __future__ import annotations

import datetime as dt
import os
import re
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.config import market_today
from src.gateway.adapters.mcp_client import McpReadClient
from src.gateway.types import Bar, ContractKind, Headline, OptionContract, Quote

DEFAULT_MCP_URL = "https://agent.robinhood.com/mcp/trading"
DEFAULT_TOKEN_PATH = "data/robinhood_token.json"
QUOTE_BATCH = 40

_FRACTION = re.compile(r"(\.\d{6})\d+")


def settings_from_env() -> tuple[str, Path]:
    url = os.environ.get("ROBINHOOD_MCP_URL", DEFAULT_MCP_URL)
    path = Path(os.environ.get("ROBINHOOD_TOKEN_PATH", DEFAULT_TOKEN_PATH))
    return url, path


def _dec(value: object) -> Decimal:
    return Decimal(str(value)) if value not in (None, "") else Decimal("0")


def _dec_or_none(value: object) -> Decimal | None:
    return None if value in (None, "") else Decimal(str(value))


def _ts(value: str) -> dt.datetime:
    cleaned = _FRACTION.sub(r"\1", value.replace("Z", "+00:00"))
    parsed = dt.datetime.fromisoformat(cleaned)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _kind(value: object) -> ContractKind | None:
    if value == "call":
        return "call"
    if value == "put":
        return "put"
    return None


class RobinhoodAdapter:
    def __init__(
        self,
        client: McpReadClient | None = None,
        today: Callable[[], dt.date] = market_today,
    ) -> None:
        if client is None:
            url, path = settings_from_env()
            client = McpReadClient(url, path)
        self._client = client
        self._today = today

    def close(self) -> None:
        self._client.close()

    def _data(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        data = self._client.call(tool, arguments).get("data")
        return data if isinstance(data, dict) else {}

    def get_quote(self, ticker: str) -> Quote:
        results = self._data("get_equity_quotes", {"symbols": [ticker]}).get("results") or []
        if not results:
            raise LookupError(f"no quote returned for {ticker}")
        q = results[0]["quote"]
        return Quote(
            ticker=ticker,
            last=_dec(q.get("last_trade_price")),
            bid=_dec(q.get("bid_price")),
            ask=_dec(q.get("ask_price")),
            previous_close=_dec(q.get("adjusted_previous_close") or q.get("previous_close")),
            as_of=_ts(q["venue_last_trade_time"]),
        )

    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]:
        today = self._today()
        chains = self._data("get_option_chains", {"underlying_symbol": ticker}).get("chains") or []
        contracts: list[OptionContract] = []
        for chain in chains:
            if chain.get("symbol") != ticker or not chain.get("can_open_position", True):
                continue
            expiries = [
                e
                for e in chain.get("expiration_dates") or []
                if min_dte <= (dt.date.fromisoformat(e) - today).days <= max_dte
            ]
            if not expiries:
                continue
            instruments = self._instruments(chain["id"], expiries)
            quotes = self._quotes([i["id"] for i in instruments])
            for inst in instruments:
                q = quotes.get(inst["id"])
                kind = _kind(inst.get("type"))
                if q is None or kind is None:
                    continue
                contracts.append(
                    OptionContract(
                        contract_id=inst["id"],
                        ticker=ticker,
                        contract_type=kind,
                        strike=_dec(inst["strike_price"]),
                        expiry=dt.date.fromisoformat(inst["expiration_date"]),
                        bid=_dec(q.get("bid_price")),
                        ask=_dec(q.get("ask_price")),
                        volume=int(q.get("volume") or 0),
                        open_interest=int(q.get("open_interest") or 0),
                        implied_vol=_dec_or_none(q.get("implied_volatility")),
                    )
                )
        return contracts

    def _instruments(self, chain_id: str, expiries: list[str]) -> list[dict[str, Any]]:
        base = {"chain_id": chain_id, "expiration_dates": ",".join(expiries), "state": "active"}
        out: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            args = dict(base)
            if cursor:
                args["cursor"] = cursor
            data = self._data("get_option_instruments", args)
            out.extend(
                i for i in data.get("instruments") or [] if i.get("tradability") == "tradable"
            )
            nxt = data.get("next")
            if not nxt:
                return out
            cursors = parse_qs(urlparse(str(nxt)).query).get("cursor")
            cursor = cursors[0] if cursors else None
            if not cursor:
                return out

    def _quotes(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for start in range(0, len(ids), QUOTE_BATCH):
            batch = ids[start : start + QUOTE_BATCH]
            data = self._data("get_option_quotes", {"instrument_ids": batch})
            for entry in data.get("results") or []:
                q = entry.get("quote")
                if q and q.get("instrument_id"):
                    out[q["instrument_id"]] = q
        return out

    def get_historicals(self, ticker: str, days: int) -> list[Bar]:
        start = dt.datetime.now(dt.UTC) - dt.timedelta(days=days * 2 + 7)
        data = self._data(
            "get_equity_historicals",
            {
                "symbols": [ticker],
                "start_time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "interval": "day",
            },
        )
        results = data.get("results") or []
        raw_bars = (results[0].get("bars") if results else None) or []
        bars = [
            Bar(
                date=_ts(raw["begins_at"]).date(),
                open=_dec(raw.get("open_price")),
                high=_dec(raw.get("high_price")),
                low=_dec(raw.get("low_price")),
                close=_dec(raw.get("close_price")),
                volume=int(raw.get("volume") or 0),
            )
            for raw in raw_bars
            if not raw.get("interpolated")
        ]
        return bars[-days:]

    def get_earnings_date(self, ticker: str) -> dt.date | None:
        today = self._today()
        upcoming: list[dt.date] = []
        for entry in self._data("get_earnings_results", {"symbol": ticker}).get("results") or []:
            report = entry.get("report") or {}
            eps = entry.get("eps") or {}
            raw_date = report.get("date")
            if raw_date and eps.get("actual") is None:
                day = dt.date.fromisoformat(raw_date)
                if day >= today:
                    upcoming.append(day)
        return min(upcoming) if upcoming else None

    def get_news(self, ticker: str, limit: int) -> list[Headline]:
        articles = self._data("get_equity_news", {"symbol": ticker, "limit": limit}).get(
            "articles"
        )
        return [
            Headline(
                title=a.get("title") or "",
                publisher=a.get("publisher") or "",
                published_at=_ts(a["published_at"]),
            )
            for a in (articles or [])[:limit]
            if a.get("published_at")
        ]
