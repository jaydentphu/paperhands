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
    # 100 -> 120 over 21 bars: return = 0.20 (> 0.03), all up days: RSI = 100 (> 55)
    return [_bar(i, Decimal(100 + i)) for i in range(21)]


def _bearish_bars() -> list[Bar]:
    # 120 -> 100 over 21 bars: return = -0.1667 (< -0.03), all down days: RSI = 0 (< 45)
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


def test_screen_bullish_picks_long_call_closest_to_35_dte_and_atm() -> None:
    spot = Decimal(120)
    contracts = [
        _contract("c-far-dte", ContractType.CALL, Decimal(120), dte=45),
        _contract("c-near-dte-near-strike", ContractType.CALL, Decimal(120), dte=34),
        _contract("p-1", ContractType.PUT, Decimal(120), dte=35),
    ]
    result = screen(_bullish_bars(), contracts, spot, TODAY)
    assert result.action == Action.LONG_CALL
    assert result.contract is not None
    assert result.contract.contract_id == "c-near-dte-near-strike"


def test_screen_never_drifts_past_the_moneyness_cap_even_for_a_perfect_dte_match() -> None:
    """Regression test for the exact bug the strategy review caught: with no
    moneyness cap, a far-OTM contract with dte distance 0 used to beat a
    near-ATM contract with dte distance 1, because distance() compared DTE
    first. The moneyness filter must exclude the far-strike contract before
    that comparison ever happens."""
    spot = Decimal(120)
    contracts = [
        _contract("c-perfect-dte-far-strike", ContractType.CALL, Decimal(150), dte=35),
        _contract("c-good-dte-near-strike", ContractType.CALL, Decimal(120), dte=34),
    ]
    result = screen(_bullish_bars(), contracts, spot, TODAY)
    assert result.action == Action.LONG_CALL
    assert result.contract is not None
    assert result.contract.contract_id == "c-good-dte-near-strike"


def test_screen_moneyness_cap_excludes_everything_is_no_trade() -> None:
    spot = Decimal(120)
    contracts = [_contract("c-far-otm", ContractType.CALL, Decimal(200), dte=35)]
    result = screen(_bullish_bars(), contracts, spot, TODAY)
    assert result.action == Action.NO_TRADE
    assert result.contract is None


def test_screen_bearish_picks_long_put() -> None:
    contracts = [
        _contract("p-far", ContractType.PUT, Decimal(100), dte=44),
        _contract("p-near", ContractType.PUT, Decimal(100), dte=35),
        _contract("c-1", ContractType.CALL, Decimal(100), dte=35),
    ]
    result = screen(_bearish_bars(), contracts, Decimal(100), TODAY)
    assert result.action == Action.LONG_PUT
    assert result.contract is not None
    assert result.contract.contract_id == "p-near"


def test_screen_neutral_indicators_is_no_trade() -> None:
    contracts = [_contract("c-1", ContractType.CALL, Decimal(100), dte=35)]
    result = screen(_flat_bars(), contracts, Decimal(100), TODAY)
    assert result.action == Action.NO_TRADE
    assert result.contract is None


def test_screen_bullish_signal_but_no_eligible_calls_is_no_trade() -> None:
    contracts = [_contract("p-1", ContractType.PUT, Decimal(120), dte=35)]
    result = screen(_bullish_bars(), contracts, Decimal(120), TODAY)
    assert result.action == Action.NO_TRADE
    assert result.contract is None


def test_screen_no_trade_when_earnings_falls_within_the_horizon() -> None:
    # TODAY = Wed 2026-09-16; horizon exit (5 trading days) = Wed 2026-09-23.
    contracts = [_contract("c-1", ContractType.CALL, Decimal(120), dte=35)]
    result = screen(
        _bullish_bars(), contracts, Decimal(120), TODAY, earnings_date=dt.date(2026, 9, 20)
    )
    assert result.action == Action.NO_TRADE
    assert result.contract is None


def test_screen_no_trade_when_earnings_is_today() -> None:
    contracts = [_contract("c-1", ContractType.CALL, Decimal(120), dte=35)]
    result = screen(_bullish_bars(), contracts, Decimal(120), TODAY, earnings_date=TODAY)
    assert result.action == Action.NO_TRADE


def test_screen_trades_normally_when_earnings_is_after_the_horizon() -> None:
    contracts = [_contract("c-1", ContractType.CALL, Decimal(120), dte=35)]
    result = screen(
        _bullish_bars(), contracts, Decimal(120), TODAY, earnings_date=dt.date(2026, 9, 25)
    )
    assert result.action == Action.LONG_CALL
    assert result.contract is not None


def test_screen_trades_normally_when_no_earnings_date_is_known() -> None:
    contracts = [_contract("c-1", ContractType.CALL, Decimal(120), dte=35)]
    result = screen(_bullish_bars(), contracts, Decimal(120), TODAY, earnings_date=None)
    assert result.action == Action.LONG_CALL
