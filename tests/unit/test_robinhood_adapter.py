"""Maps canned Robinhood MCP payloads (shapes captured from the live server
during Stage 2) through RobinhoodAdapter without any network."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

import pytest

from src.gateway.adapters.mcp_client import READ_TOOLS
from src.gateway.adapters.robinhood import RobinhoodAdapter

TODAY = dt.date(2026, 9, 16)
CHAIN_ID = "7dd906e5-7d4b-4161-a3fe-2c3b62038482"


class StubClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool, arguments))
        response = self._responses[tool]
        if isinstance(response, list):
            return dict(response.pop(0))
        return dict(response)

    def close(self) -> None:
        pass


def _instrument(
    instrument_id: str, strike: str, kind: str, tradability: str = "tradable"
) -> dict[str, Any]:
    return {
        "id": instrument_id,
        "chain_id": CHAIN_ID,
        "chain_symbol": "AAPL",
        "expiration_date": "2026-10-16",
        "strike_price": strike,
        "type": kind,
        "state": "active",
        "tradability": tradability,
    }


def _option_quote(instrument_id: str, bid: str, ask: str, oi: int) -> dict[str, Any]:
    return {
        "quote": {
            "instrument_id": instrument_id,
            "ask_price": ask,
            "bid_price": bid,
            "implied_volatility": "0.251308",
            "open_interest": oi,
            "volume": 3101,
        }
    }


@pytest.fixture
def responses() -> dict[str, Any]:
    return {
        "get_equity_quotes": {
            "data": {
                "results": [
                    {
                        "quote": {
                            "symbol": "AAPL",
                            "last_trade_price": "331.335000",
                            "venue_last_trade_time": "2026-09-15T19:59:59.9866216Z",
                            "adjusted_previous_close": "331.340000",
                            "previous_close": "331.340000",
                            "bid_price": "331.540000",
                            "ask_price": "331.640000",
                        }
                    }
                ]
            }
        },
        "get_option_chains": {
            "data": {
                "chains": [
                    {
                        "id": CHAIN_ID,
                        "symbol": "AAPL",
                        "can_open_position": True,
                        "expiration_dates": [
                            "2026-09-18",
                            "2026-10-02",
                            "2026-10-16",
                            "2026-10-30",
                            "2026-11-20",
                        ],
                    },
                    {"id": "other", "symbol": "AAPL1", "can_open_position": True,
                     "expiration_dates": ["2026-10-16"]},
                ]
            }
        },
        "get_option_instruments": [
            {
                "data": {
                    "instruments": [
                        _instrument("i-330c", "330.0000", "call"),
                        _instrument("i-330p", "330.0000", "put"),
                        _instrument("i-dead", "335.0000", "call", tradability="untradable"),
                    ],
                    "next": "https://api.example/instruments/?cursor=abc123",
                }
            },
            {"data": {"instruments": [_instrument("i-335p", "335.0000", "put")], "next": None}},
        ],
        "get_option_quotes": {
            "data": {
                "results": [
                    _option_quote("i-330c", "10.600000", "11.000000", 15948),
                    _option_quote("i-330p", "8.100000", "8.300000", 11499),
                    {"quote": None},
                ]
            }
        },
        "get_equity_historicals": {
            "data": {
                "results": [
                    {
                        "symbol": "AAPL",
                        "bars": [
                            {"begins_at": "2026-09-10T00:00:00Z", "open_price": "316.67",
                             "close_price": "326.57", "high_price": "326.74",
                             "low_price": "316.51", "volume": 70011913},
                            {"begins_at": "2026-09-11T00:00:00Z", "open_price": "327.45",
                             "close_price": "332.27", "high_price": "336.22",
                             "low_price": "326.30", "volume": 50716865, "interpolated": True},
                            {"begins_at": "2026-09-14T00:00:00Z", "open_price": "334.79",
                             "close_price": "333.08", "high_price": "335.50",
                             "low_price": "331.34", "volume": 39269147},
                            {"begins_at": "2026-09-15T00:00:00Z", "open_price": "330.135",
                             "close_price": "331.34", "high_price": "331.78",
                             "low_price": "328.35", "volume": 31748183},
                        ],
                    }
                ]
            }
        },
        "get_earnings_results": {
            "data": {
                "results": [
                    {"symbol": "AAPL", "eps": {"estimate": "1.89", "actual": "2.02"},
                     "report": {"date": "2026-07-30", "timing": "pm"}},
                    {"symbol": "AAPL", "eps": {"estimate": "1.98", "actual": None},
                     "report": {"date": "2026-10-29", "timing": "pm", "verified": False}},
                ]
            }
        },
        "get_equity_news": {
            "data": {
                "articles": [
                    {"title": "What's Going On With Apple Stock Tuesday?", "publisher": "Benzinga",
                     "published_at": "2026-09-15T10:18:52-04:00"},
                    {"title": "No timestamp", "publisher": "X"},
                ]
            }
        },
    }


@pytest.fixture
def adapter(responses: dict[str, Any]) -> tuple[RobinhoodAdapter, StubClient]:
    client = StubClient(responses)
    return RobinhoodAdapter(client=client, today=lambda: TODAY), client


def test_quote_maps_prices_as_decimal(adapter: tuple[RobinhoodAdapter, StubClient]) -> None:
    rh, _ = adapter
    quote = rh.get_quote("AAPL")
    assert quote.last == Decimal("331.335000")
    assert quote.bid == Decimal("331.540000")
    assert quote.previous_close == Decimal("331.340000")
    assert quote.as_of == dt.datetime(2026, 9, 15, 19, 59, 59, 986621, tzinfo=dt.UTC)


def test_option_chain_filters_window_paginates_and_batches(
    adapter: tuple[RobinhoodAdapter, StubClient],
) -> None:
    rh, client = adapter
    contracts = rh.get_option_chain("AAPL", 14, 45)

    instrument_calls = [a for t, a in client.calls if t == "get_option_instruments"]
    assert len(instrument_calls) == 2
    assert instrument_calls[0]["chain_id"] == CHAIN_ID
    assert instrument_calls[0]["expiration_dates"] == "2026-10-02,2026-10-16,2026-10-30"
    assert instrument_calls[1]["cursor"] == "abc123"

    quote_calls = [a for t, a in client.calls if t == "get_option_quotes"]
    assert len(quote_calls) == 1
    assert quote_calls[0]["instrument_ids"] == ["i-330c", "i-330p", "i-335p"]

    assert [c.contract_id for c in contracts] == ["i-330c", "i-330p"]
    call = contracts[0]
    assert call.contract_type == "call"
    assert call.strike == Decimal("330.0000")
    assert call.expiry == dt.date(2026, 10, 16)
    assert call.ask == Decimal("11.000000")
    assert call.open_interest == 15948
    assert call.implied_vol == Decimal("0.251308")


def test_historicals_skip_interpolated_and_take_last_n(
    adapter: tuple[RobinhoodAdapter, StubClient],
) -> None:
    rh, client = adapter
    bars = rh.get_historicals("AAPL", 2)
    assert [b.date for b in bars] == [dt.date(2026, 9, 14), dt.date(2026, 9, 15)]
    assert bars[-1].close == Decimal("331.34")
    args = client.calls[-1][1]
    assert args["interval"] == "day" and args["symbols"] == ["AAPL"]


def test_earnings_date_is_next_unreported(adapter: tuple[RobinhoodAdapter, StubClient]) -> None:
    rh, _ = adapter
    assert rh.get_earnings_date("AAPL") == dt.date(2026, 10, 29)


def test_news_maps_headlines(adapter: tuple[RobinhoodAdapter, StubClient]) -> None:
    rh, _ = adapter
    headlines = rh.get_news("AAPL", 5)
    assert len(headlines) == 1
    assert headlines[0].publisher == "Benzinga"
    assert headlines[0].published_at.utcoffset() == dt.timedelta(hours=-4)


def test_adapter_only_names_read_tools(adapter: tuple[RobinhoodAdapter, StubClient]) -> None:
    rh, client = adapter
    rh.get_quote("AAPL")
    rh.get_option_chain("AAPL", 14, 45)
    rh.get_historicals("AAPL", 20)
    rh.get_earnings_date("AAPL")
    rh.get_news("AAPL", 5)
    assert {tool for tool, _ in client.calls} <= READ_TOOLS
