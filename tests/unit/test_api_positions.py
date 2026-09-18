from __future__ import annotations

import datetime as dt
from decimal import Decimal

from src.api.main import _unrealized_pnl
from src.models import PaperPosition
from src.models.enums import Cohort, PositionStatus


def _position(status: PositionStatus, open_price: str) -> PaperPosition:
    return PaperPosition(
        id=1,
        cohort=Cohort.C,
        decision_id=1,
        contract_id="A1",
        expiry=dt.date(2026, 4, 10),
        opened_at=dt.datetime(2026, 3, 2, 14, 30, tzinfo=dt.UTC),
        open_price=Decimal(open_price),
        underlying_open=Decimal("100"),
        quantity=1,
        max_loss=Decimal(open_price) * 100,
        status=status,
    )


def test_unrealized_pnl_for_open_position_with_a_mark() -> None:
    position = _position(PositionStatus.OPEN, "2.50")
    assert _unrealized_pnl(position, Decimal("3.30")) == Decimal("80.00")


def test_unrealized_pnl_is_none_without_a_mark_yet() -> None:
    position = _position(PositionStatus.OPEN, "2.50")
    assert _unrealized_pnl(position, None) is None


def test_unrealized_pnl_is_none_for_a_closed_position_even_with_a_mark() -> None:
    position = _position(PositionStatus.CLOSED, "2.50")
    assert _unrealized_pnl(position, Decimal("3.30")) is None


def test_unrealized_pnl_scales_with_quantity() -> None:
    position = _position(PositionStatus.OPEN, "2.50")
    position.quantity = 3
    assert _unrealized_pnl(position, Decimal("3.00")) == Decimal("150.00")
