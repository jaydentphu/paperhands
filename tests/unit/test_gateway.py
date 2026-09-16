from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from src.config import DTE_MAX, DTE_MIN
from src.gateway import ALLOWLIST, CapabilityError, DataGateway
from src.gateway.adapters.fake import FakeAdapter

TODAY = dt.date(2026, 9, 16)


@pytest.fixture
def gateway() -> DataGateway:
    return DataGateway(FakeAdapter(today=lambda: TODAY))


def test_allowlist_is_exactly_the_five_read_functions() -> None:
    assert ALLOWLIST == (
        "get_quote",
        "get_option_chain",
        "get_historicals",
        "get_earnings_date",
        "get_news",
    )


def test_public_surface_is_allowlist_plus_tools() -> None:
    public = {name for name in dir(DataGateway) if not name.startswith("_")}
    assert public == set(ALLOWLIST) | {"tools"}


def test_unknown_name_raises_capability_error(gateway: DataGateway) -> None:
    with pytest.raises(CapabilityError):
        gateway.fetch_anything  # noqa: B018
    with pytest.raises(CapabilityError):
        gateway.download_everything()


def test_tools_are_the_bound_allowlist_functions_in_order(gateway: DataGateway) -> None:
    tools = gateway.tools()
    assert tuple(t.__name__ for t in tools) == ALLOWLIST
    assert all(getattr(t, "is_mutating", True) is False for t in tools)
    assert tools[0]("AAPL").ticker == "AAPL"


def test_gateway_delegates_to_adapter(gateway: DataGateway) -> None:
    quote = gateway.get_quote("AAPL")
    assert isinstance(quote.last, Decimal)
    assert quote.ask > quote.bid
    assert len(gateway.get_historicals("AAPL", 20)) == 20
    assert len(gateway.get_news("AAPL", 3)) == 3
    assert gateway.get_earnings_date("AAPL") is None or gateway.get_earnings_date("AAPL") > TODAY


def test_option_chain_stays_inside_dte_window(gateway: DataGateway) -> None:
    contracts = gateway.get_option_chain("AAPL", DTE_MIN, DTE_MAX)
    assert contracts
    assert all(DTE_MIN <= c.dte(TODAY) <= DTE_MAX for c in contracts)
    assert {c.contract_type for c in contracts} == {"call", "put"}
    assert len({c.contract_id for c in contracts}) == len(contracts)


def test_fake_adapter_is_deterministic() -> None:
    a = FakeAdapter(today=lambda: TODAY).get_option_chain("MSFT", DTE_MIN, DTE_MAX)
    b = FakeAdapter(today=lambda: TODAY).get_option_chain("MSFT", DTE_MIN, DTE_MAX)
    assert a == b


def test_fake_chain_mixes_eligible_and_ineligible(gateway: DataGateway) -> None:
    contracts = gateway.get_option_chain("NVDA", DTE_MIN, DTE_MAX)
    assert any(c.open_interest < 500 for c in contracts)
    assert any(c.open_interest >= 500 for c in contracts)
    assert any(c.ask * 100 > Decimal("300") for c in contracts)
    assert any(Decimal(0) < c.ask * 100 <= Decimal("300") for c in contracts)
