from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from src.gateway.types import Bar
from src.screener.indicators import rsi_14, twenty_day_return


def _bar(day: int, close: Decimal) -> Bar:
    date = dt.date(2026, 1, 1) + dt.timedelta(days=day)
    return Bar(date=date, open=close, high=close, low=close, close=close, volume=1)


def test_twenty_day_return_uses_last_21_bars_not_first() -> None:
    noise = [_bar(i, Decimal(9999)) for i in range(4)]
    window = [_bar(4 + i, Decimal(100) + Decimal("0.5") * i) for i in range(21)]
    assert twenty_day_return(noise + window) == Decimal("0.10")


def test_twenty_day_return_requires_21_bars() -> None:
    with pytest.raises(ValueError, match="21 bars"):
        twenty_day_return([_bar(i, Decimal(100)) for i in range(20)])


def test_rsi_all_gains_is_100() -> None:
    bars = [_bar(i, Decimal(100 + i)) for i in range(15)]
    assert rsi_14(bars) == Decimal(100)


def test_rsi_all_losses_is_0() -> None:
    bars = [_bar(i, Decimal(100 - i)) for i in range(15)]
    assert rsi_14(bars) == Decimal(0)


def test_rsi_hand_computed_mixed_gains_and_losses() -> None:
    closes = [Decimal(100)]
    for change in [Decimal(2), Decimal(-1)] * 7:
        closes.append(closes[-1] + change)
    assert len(closes) == 15
    bars = [_bar(i, close) for i, close in enumerate(closes)]
    # 7 up days of +2 (gains=14, avg_gain=1), 7 down days of -1 (losses=7,
    # avg_loss=0.5): RS = 2, RSI = 100 - 100/(1+2) = 100 - 100/3
    assert rsi_14(bars) == Decimal(100) - (Decimal(100) / Decimal(3))


def test_rsi_requires_15_bars() -> None:
    with pytest.raises(ValueError, match="15 bars"):
        rsi_14([_bar(i, Decimal(100)) for i in range(14)])
