from __future__ import annotations

from src.models.enums import Action
from src.screener.cash import decide


def test_cash_cohort_always_decides_no_trade() -> None:
    assert decide() == Action.NO_TRADE
