"""The only tools the research agent ever receives: the DataGateway's
allowlisted read functions, verbatim. No wrapping, no extras.

tool_definitions() renders them for the API; dispatch() routes a tool call
back to the gateway by name - only names in ALLOWLIST, anything else raises
CapabilityError before touching the gateway."""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from src.gateway import ALLOWLIST, CapabilityError, DataGateway

MAX_HISTORICAL_DAYS = 60
MAX_NEWS = 20
MAX_DTE = 365

_TICKER = {"type": "string", "description": "Ticker symbol, e.g. AAPL"}

_INPUT_SCHEMAS: dict[str, tuple[str, dict[str, Any]]] = {
    "get_quote": (
        "Current quote for a ticker: last, bid, ask, previous close.",
        {"ticker": _TICKER},
    ),
    "get_option_chain": (
        "Option contracts for a ticker with days-to-expiry between min_dte and max_dte, "
        "with bid, ask, volume, open interest, and implied volatility. Note that only the "
        "ELIGIBLE CONTRACTS in the bundle may be chosen.",
        {
            "ticker": _TICKER,
            "min_dte": {"type": "integer", "description": "Minimum days to expiry"},
            "max_dte": {"type": "integer", "description": "Maximum days to expiry"},
        },
    ),
    "get_historicals": (
        f"Daily OHLCV bars for the trailing N days (max {MAX_HISTORICAL_DAYS}).",
        {"ticker": _TICKER, "days": {"type": "integer", "description": "Number of daily bars"}},
    ),
    "get_earnings_date": (
        "Next scheduled earnings report date for a ticker, or null.",
        {"ticker": _TICKER},
    ),
    "get_news": (
        f"Recent headlines for a ticker (max {MAX_NEWS}).",
        {"ticker": _TICKER, "limit": {"type": "integer", "description": "How many headlines"}},
    ),
}


def agent_tool_list(gateway: DataGateway) -> tuple[Callable[..., object], ...]:
    return gateway.tools()


def tool_definitions() -> list[dict[str, Any]]:
    defs: list[dict[str, Any]] = []
    for name in ALLOWLIST:
        description, properties = _INPUT_SCHEMAS[name]
        defs.append(
            {
                "name": name,
                "description": description,
                "strict": True,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                    "additionalProperties": False,
                },
            }
        )
    return defs


def _clamp(value: object, low: int, high: int) -> int:
    number = low
    if isinstance(value, int | float) and not isinstance(value, bool):
        number = int(value)
    elif isinstance(value, str):
        try:
            number = int(float(value))
        except ValueError:
            number = low
    return max(low, min(high, number))


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def dispatch(gateway: DataGateway, name: str, arguments: dict[str, Any]) -> str:
    if name not in ALLOWLIST:
        raise CapabilityError(name)
    ticker = str(arguments.get("ticker", "")).upper()
    if name == "get_quote":
        result: object = gateway.get_quote(ticker)
    elif name == "get_option_chain":
        result = gateway.get_option_chain(
            ticker,
            _clamp(arguments.get("min_dte"), 0, MAX_DTE),
            _clamp(arguments.get("max_dte"), 0, MAX_DTE),
        )
    elif name == "get_historicals":
        days = _clamp(arguments.get("days"), 1, MAX_HISTORICAL_DAYS)
        result = gateway.get_historicals(ticker, days)
    elif name == "get_earnings_date":
        result = gateway.get_earnings_date(ticker)
    else:
        result = gateway.get_news(ticker, _clamp(arguments.get("limit"), 1, MAX_NEWS))
    return json.dumps(_jsonable(result))
