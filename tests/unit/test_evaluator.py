from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from src.evaluator import evaluate_position, max_drawdown, median
from src.models import PaperPosition
from src.models.enums import Action, Cohort, PositionStatus


def _closed_position(
    open_price: str,
    close_price: str,
    underlying_open: str,
    underlying_close: str,
    opened: dt.date = dt.date(2026, 3, 2),
    closed: dt.date = dt.date(2026, 3, 9),
) -> PaperPosition:
    return PaperPosition(
        id=7,
        cohort=Cohort.B,
        decision_id=1,
        contract_id="A1",
        expiry=dt.date(2026, 4, 10),
        opened_at=dt.datetime.combine(opened, dt.time(10, 30), tzinfo=dt.UTC),
        open_price=Decimal(open_price),
        underlying_open=Decimal(underlying_open),
        underlying_close=Decimal(underlying_close),
        quantity=1,
        max_loss=Decimal(open_price) * 100,
        status=PositionStatus.CLOSED,
        closed_at=dt.datetime.combine(closed, dt.time(16, 15), tzinfo=dt.UTC),
        close_price=Decimal(close_price),
    )


def test_evaluate_call_that_won() -> None:
    ev = evaluate_position(_closed_position("2.50", "3.30", "200", "206"), Action.LONG_CALL)
    assert ev.position_id == 7
    assert ev.realized_pnl == Decimal("80.00")
    assert ev.direction_correct is True
    assert ev.horizon_days == 5


def test_evaluate_put_when_underlying_rose_is_wrong_direction() -> None:
    ev = evaluate_position(_closed_position("2.20", "1.40", "400", "404"), Action.LONG_PUT)
    assert ev.realized_pnl == Decimal("-80.00")
    assert ev.direction_correct is False


def test_evaluate_put_when_underlying_fell_is_correct() -> None:
    ev = evaluate_position(_closed_position("2.60", "3.50", "402", "396"), Action.LONG_PUT)
    assert ev.realized_pnl == Decimal("90.00")
    assert ev.direction_correct is True


def test_unchanged_underlying_counts_as_wrong_direction() -> None:
    ev = evaluate_position(_closed_position("2.00", "2.00", "100", "100"), Action.LONG_CALL)
    assert ev.realized_pnl == Decimal("0")
    assert ev.direction_correct is False


def test_evaluate_refuses_no_trade_and_unclosed_positions() -> None:
    with pytest.raises(ValueError):
        evaluate_position(_closed_position("2", "2", "1", "1"), Action.NO_TRADE)
    unclosed = _closed_position("2", "2", "1", "1")
    unclosed.close_price = None
    with pytest.raises(ValueError):
        evaluate_position(unclosed, Action.LONG_CALL)


def test_median_odd_even_and_empty() -> None:
    assert median([Decimal(80), Decimal(-80), Decimal(10)]) == Decimal(10)
    assert median([Decimal(10), Decimal(40)]) == Decimal(25)
    assert median([]) == Decimal(0)


def test_max_drawdown_from_zero_start() -> None:
    assert max_drawdown([]) == Decimal(0)
    assert max_drawdown([Decimal(-50)]) == Decimal(50)
    assert max_drawdown([Decimal(80), Decimal(-80), Decimal(10)]) == Decimal(80)
    assert max_drawdown([Decimal(40), Decimal(-110), Decimal(90)]) == Decimal(110)
    assert max_drawdown([Decimal(10), Decimal(20), Decimal(30)]) == Decimal(0)
