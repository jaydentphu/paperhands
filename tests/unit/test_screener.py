from __future__ import annotations

import datetime as dt
from decimal import Decimal

from src.gateway.types import Bar
from src.models import ContractSnapshot
from src.models.enums import Action, ContractType
from src.screener.screener import screen

TODAY = dt.date(2026, 9, 16)


def _bar(i: int, close: Decimal) -> Bar:
    date = TODAY - dt.timedelta(days=21 - i)
    return Bar(date=date, open=close, high=close, low=close, close=close, volume=1)


def _bullish_bars() -> list[Bar]:
    # 100 -> 120 over 21 bars: return = 0.20 (> 0.02), all up days: RSI = 100 (> 55)
    return [_bar(i, Decimal(100 + i)) for i in range(21)]


def _bearish_bars() -> list[Bar]:
    # 120 -> 100 over 21 bars: return = -0.1667 (< -0.02), all down days: RSI = 0 (< 45)
    return [_bar(i, Decimal(120 - i)) for i in range(21)]


def _flat_bars() -> list[Bar]:
    # no movement at all: return = 0.0, well inside the neutral band
    return [_bar(i, Decimal(100)) for i in range(21)]


def _contract(
    contract_id: str, contract_type: ContractType, strike: Decimal, dte: int
) -> ContractSnapshot:
    return ContractSnapshot(
        snapshot_id=1,
        contract_id=contract_id,
        contract_type=contract_type,
        strike=strike,
        expiry=TODAY + dt.timedelta(days=dte),
        bid=Decimal("1.00"),
        ask=Decimal("1.20"),
        volume=100,
        open_interest=1000,
        implied_vol=Decimal("0.3"),
        eligible=True,
        ineligible_reason=None,
    )


def test_screen_bullish_picks_long_call_closest_to_30_dte_and_atm() -> None:
    spot = Decimal(120)
    contracts = [
        _contract("c-far-dte", ContractType.CALL, Decimal(120), dte=45),
        _contract("c-near-dte-far-strike", ContractType.CALL, Decimal(150), dte=31),
        _contract("c-near-dte-near-strike", ContractType.CALL, Decimal(120), dte=29),
        _contract("p-1", ContractType.PUT, Decimal(120), dte=30),
    ]
    result = screen(_bullish_bars(), contracts, spot, TODAY)
    assert result.action == Action.LONG_CALL
    assert result.contract is not None
    assert result.contract.contract_id == "c-near-dte-near-strike"


def test_screen_bearish_picks_long_put() -> None:
    contracts = [
        _contract("p-far", ContractType.PUT, Decimal(100), dte=44),
        _contract("p-near", ContractType.PUT, Decimal(100), dte=30),
        _contract("c-1", ContractType.CALL, Decimal(100), dte=30),
    ]
    result = screen(_bearish_bars(), contracts, Decimal(100), TODAY)
    assert result.action == Action.LONG_PUT
    assert result.contract is not None
    assert result.contract.contract_id == "p-near"


def test_screen_neutral_indicators_is_no_trade() -> None:
    contracts = [_contract("c-1", ContractType.CALL, Decimal(100), dte=30)]
    result = screen(_flat_bars(), contracts, Decimal(100), TODAY)
    assert result.action == Action.NO_TRADE
    assert result.contract is None


def test_screen_bullish_signal_but_no_eligible_calls_is_no_trade() -> None:
    contracts = [_contract("p-1", ContractType.PUT, Decimal(120), dte=30)]
    result = screen(_bullish_bars(), contracts, Decimal(120), TODAY)
    assert result.action == Action.NO_TRADE
    assert result.contract is None
