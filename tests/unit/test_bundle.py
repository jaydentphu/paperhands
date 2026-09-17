from __future__ import annotations

import dataclasses
import datetime as dt
from decimal import Decimal

from src.agent.bundle import BundleContract, BundleInputs, build_bundle

TODAY = dt.date(2026, 9, 16)


def _inputs(**overrides: object) -> BundleInputs:
    base = BundleInputs(
        ticker="AAPL",
        as_of=TODAY,
        quote={"last": "331.335", "bid": "331.54", "ask": "331.64", "previous_close": "331.34"},
        twenty_day_return=Decimal("0.0412"),
        rsi_14=Decimal("62.34"),
        earnings_date=dt.date(2026, 10, 29),
        headlines=[
            {"title": f"headline {i}", "publisher": "Wire", "published_at": "2026-09-15T10:00:00"}
            for i in range(8)
        ],
        eligible_contracts=[
            BundleContract(
                contract_id="abc-1",
                contract_type="call",
                strike=Decimal("340"),
                expiry=dt.date(2026, 10, 16),
                dte=30,
                bid=Decimal("2.10"),
                ask=Decimal("2.30"),
                open_interest=15948,
                implied_vol=Decimal("0.251308"),
            )
        ],
    )
    return dataclasses.replace(base, **overrides)  # type: ignore[arg-type]


def test_bundle_contains_every_section_and_the_contract_row() -> None:
    text = build_bundle(_inputs())
    assert "TICKER: AAPL" in text
    assert "20-day return: +4.12%" in text
    assert "RSI(14): 62.3" in text
    assert "next report 2026-10-29 (43 days away)" in text
    assert "abc-1 | call | 340.00 | 2026-10-16 | 30 | 2.10 | 2.30 | 15948 | 0.251" in text


def test_bundle_shows_only_top_five_headlines() -> None:
    text = build_bundle(_inputs())
    assert "headline 4" in text
    assert "headline 5" not in text


def test_bundle_handles_missing_indicators_and_contracts() -> None:
    text = build_bundle(
        _inputs(twenty_day_return=None, rsi_14=None, earnings_date=None, eligible_contracts=[])
    )
    assert "20-day return: n/a" in text
    assert "RSI(14): n/a" in text
    assert "no upcoming report date known" in text
    assert "the only valid action is no_trade" in text


def test_bundle_cannot_carry_pnl_or_past_decisions() -> None:
    field_names = {f.name for f in dataclasses.fields(BundleInputs)}
    assert not field_names & {"pnl", "realized_pnl", "positions", "decisions", "history"}
    text = build_bundle(_inputs()).lower()
    for forbidden in ("p&l", "pnl", "realized", "position", "past decision", "prior decision"):
        assert forbidden not in text
