from __future__ import annotations

from decimal import Decimal

from src.validator.eligibility import (
    DTE_OUT_OF_WINDOW,
    OPEN_INTEREST_TOO_LOW,
    PREMIUM_TOO_HIGH,
    SPREAD_TOO_WIDE,
    evaluate_contract,
)


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "dte": 30,
        "bid": Decimal("2.00"),
        "ask": Decimal("2.10"),
        "open_interest": 600,
    }
    base.update(overrides)
    return base


def test_eligible_contract_passes() -> None:
    eligible, reason = evaluate_contract(**_kwargs())
    assert eligible is True
    assert reason is None


def test_dte_below_window() -> None:
    eligible, reason = evaluate_contract(**_kwargs(dte=10))
    assert eligible is False
    assert reason == DTE_OUT_OF_WINDOW


def test_dte_above_window() -> None:
    eligible, reason = evaluate_contract(**_kwargs(dte=50))
    assert eligible is False
    assert reason == DTE_OUT_OF_WINDOW


def test_dte_at_window_edges_is_eligible() -> None:
    assert evaluate_contract(**_kwargs(dte=28))[0] is True
    assert evaluate_contract(**_kwargs(dte=45))[0] is True


def test_spread_too_wide() -> None:
    eligible, reason = evaluate_contract(**_kwargs(bid=Decimal("1.00"), ask=Decimal("1.30")))
    assert eligible is False
    assert reason == SPREAD_TOO_WIDE


def test_zero_bid_is_spread_too_wide() -> None:
    eligible, reason = evaluate_contract(**_kwargs(bid=Decimal("0.00"), ask=Decimal("1.00")))
    assert eligible is False
    assert reason == SPREAD_TOO_WIDE


def test_zero_bid_and_ask_is_spread_too_wide() -> None:
    eligible, reason = evaluate_contract(**_kwargs(bid=Decimal("0.00"), ask=Decimal("0.00")))
    assert eligible is False
    assert reason == SPREAD_TOO_WIDE


def test_open_interest_too_low() -> None:
    eligible, reason = evaluate_contract(**_kwargs(open_interest=100))
    assert eligible is False
    assert reason == OPEN_INTEREST_TOO_LOW


def test_open_interest_at_minimum_is_eligible() -> None:
    assert evaluate_contract(**_kwargs(open_interest=500))[0] is True


def test_premium_too_high() -> None:
    eligible, reason = evaluate_contract(**_kwargs(bid=Decimal("3.50"), ask=Decimal("3.60")))
    assert eligible is False
    assert reason == PREMIUM_TOO_HIGH


def test_premium_at_cap_is_eligible() -> None:
    assert evaluate_contract(**_kwargs(bid=Decimal("2.95"), ask=Decimal("3.00")))[0] is True
