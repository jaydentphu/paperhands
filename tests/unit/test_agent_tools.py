from __future__ import annotations

import datetime as dt
import json

import pytest

from src.agent.schema import OUTPUT_SCHEMA, TradeCandidate
from src.agent.tools import MAX_HISTORICAL_DAYS, dispatch, tool_definitions
from src.gateway import ALLOWLIST, CapabilityError, DataGateway
from src.gateway.adapters.fake import FakeAdapter

TODAY = dt.date(2026, 9, 16)


@pytest.fixture
def gateway() -> DataGateway:
    return DataGateway(FakeAdapter(today=lambda: TODAY))


def test_tool_definitions_are_exactly_the_allowlist_and_strict() -> None:
    defs = tool_definitions()
    assert [d["name"] for d in defs] == list(ALLOWLIST)
    assert all(d["strict"] is True for d in defs)
    assert all(d["input_schema"]["additionalProperties"] is False for d in defs)


def test_dispatch_routes_to_the_gateway(gateway: DataGateway) -> None:
    quote = json.loads(dispatch(gateway, "get_quote", {"ticker": "aapl"}))
    assert quote["ticker"] == "AAPL"
    bars = json.loads(dispatch(gateway, "get_historicals", {"ticker": "AAPL", "days": 500}))
    assert len(bars) == MAX_HISTORICAL_DAYS
    earnings = json.loads(dispatch(gateway, "get_earnings_date", {"ticker": "AAPL"}))
    assert earnings is None or earnings.startswith("20")
    news = json.loads(dispatch(gateway, "get_news", {"ticker": "AAPL", "limit": 3}))
    assert len(news) == 3


def test_dispatch_refuses_names_outside_the_allowlist(gateway: DataGateway) -> None:
    with pytest.raises(CapabilityError):
        dispatch(gateway, "fetch_everything", {"ticker": "AAPL"})


def test_output_schema_matches_the_pydantic_model() -> None:
    assert set(OUTPUT_SCHEMA["properties"]) == set(TradeCandidate.model_fields)
    assert set(OUTPUT_SCHEMA["required"]) == set(TradeCandidate.model_fields)
    assert OUTPUT_SCHEMA["additionalProperties"] is False
    assert set(OUTPUT_SCHEMA["properties"]["action"]["enum"]) == {
        "long_call",
        "long_put",
        "no_trade",
    }
