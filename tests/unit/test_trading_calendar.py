"""Hand-verifiable dates against the real 2026 NYSE holiday list."""

from __future__ import annotations

import datetime as dt

from src.config import add_trading_days, is_trading_day, next_trading_day, trading_days_between


def test_is_trading_day_flags_weekends() -> None:
    assert is_trading_day(dt.date(2026, 1, 9)) is True  # Friday
    assert is_trading_day(dt.date(2026, 1, 10)) is False  # Saturday
    assert is_trading_day(dt.date(2026, 1, 11)) is False  # Sunday
    assert is_trading_day(dt.date(2026, 1, 12)) is True  # Monday


def test_is_trading_day_flags_holidays() -> None:
    assert is_trading_day(dt.date(2026, 1, 19)) is False  # MLK Day (a Monday)
    assert is_trading_day(dt.date(2027, 1, 1)) is False  # New Year's Day 2027


def test_next_trading_day_skips_a_plain_weekend() -> None:
    assert next_trading_day(dt.date(2026, 1, 9)) == dt.date(2026, 1, 12)  # Fri -> Mon


def test_next_trading_day_skips_weekend_and_holiday_together() -> None:
    # Fri Jan 16 -> Sat 17, Sun 18, Mon 19 (MLK Day) all skipped -> Tue 20
    assert next_trading_day(dt.date(2026, 1, 16)) == dt.date(2026, 1, 20)


def test_add_trading_days_matches_next_trading_day_for_n_equals_1() -> None:
    assert add_trading_days(dt.date(2026, 1, 16), 1) == dt.date(2026, 1, 20)


def test_add_trading_days_crossing_weekend_and_holiday() -> None:
    # Mon Jan 12 + 5 trading days: Tue13, Wed14, Thu15, Fri16, then Sat17/
    # Sun18/Mon19(MLK) skipped, landing on Tue Jan 20.
    assert add_trading_days(dt.date(2026, 1, 12), 5) == dt.date(2026, 1, 20)


def test_trading_days_between_plain_weekend() -> None:
    assert trading_days_between(dt.date(2026, 1, 9), dt.date(2026, 1, 12)) == 1


def test_trading_days_between_weekend_and_holiday() -> None:
    assert trading_days_between(dt.date(2026, 1, 16), dt.date(2026, 1, 20)) == 1
    assert trading_days_between(dt.date(2026, 1, 12), dt.date(2026, 1, 20)) == 5


def test_trading_days_between_does_not_overshoot_a_non_trading_end() -> None:
    # end is a Saturday: no trading day occurs between Friday and Saturday.
    assert trading_days_between(dt.date(2026, 1, 16), dt.date(2026, 1, 17)) == 0


def test_trading_days_between_is_zero_when_end_is_not_after_start() -> None:
    assert trading_days_between(dt.date(2026, 1, 12), dt.date(2026, 1, 12)) == 0
    assert trading_days_between(dt.date(2026, 1, 12), dt.date(2026, 1, 1)) == 0


def test_add_trading_days_and_trading_days_between_are_consistent() -> None:
    start = dt.date(2026, 1, 12)
    for n in range(1, 10):
        assert trading_days_between(start, add_trading_days(start, n)) == n
