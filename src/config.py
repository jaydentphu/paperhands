"""Settings, watchlist, and thresholds for the Options Research & Evaluation Agent.

Values here come from PRD.md section 4 (eligibility defaults) and section 3
(horizon). Anything not specified by the PRD (watchlist tickers, run times,
adapter choice) is a build-time decision recorded in NOTES.md.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

Action = Literal["long_call", "long_put", "no_trade"]
AdapterName = Literal["robinhood", "yfinance", "fake"]

WATCHLIST: tuple[str, ...] = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL")

# Headlines stored per snapshot; the agent bundle (Stage 4) shows the top 5.
SNAPSHOT_NEWS_LIMIT: int = 10

# PRD section 4 eligibility defaults. DTE_MIN and MAX_SPREAD_PCT were tuned
# from the PRD's own defaults (14, 0.10) after a v1-strategy review - see
# NOTES.md Stage 4 "Strategy v1 revision". A 5-day hold starting near 14 DTE
# can finish with about a week left, where time decay accelerates; 28-45
# keeps the whole hold inside the slower-decay part of the option's life.
# 5% (down from 10%) reflects that a 5-day trade can't absorb a wide spread
# and still show a real signal.
DTE_MIN: int = 28
DTE_MAX: int = 45
MAX_SPREAD_PCT: Decimal = Decimal("0.05")
MIN_OPEN_INTEREST: int = 500
MAX_PREMIUM: Decimal = Decimal("300.00")

# PRD section 3/4: paper portfolio horizon, in trading days.
HORIZON_DAYS: int = 5

# PRD section 4: one scheduled run per trading day, after market open.
RUN_TIME: dt.time = dt.time(10, 30)
MARK_TIME: dt.time = dt.time(16, 15)
MARKET_TIMEZONE: str = "America/New_York"

# NYSE holiday calendar, hardcoded per CLAUDE.md conventions (no external
# calendar library). Observed dates only; trading-day math functions are
# below (Stage 5) - CLAUDE.md's own conventions section says that math
# lives here, in config, not in src/portfolio.
NYSE_HOLIDAYS_2026: frozenset[dt.date] = frozenset(
    {
        dt.date(2026, 1, 1),  # New Year's Day
        dt.date(2026, 1, 19),  # MLK Day
        dt.date(2026, 2, 16),  # Washington's Birthday
        dt.date(2026, 4, 3),  # Good Friday
        dt.date(2026, 5, 25),  # Memorial Day
        dt.date(2026, 6, 19),  # Juneteenth
        dt.date(2026, 7, 3),  # Independence Day (observed)
        dt.date(2026, 9, 7),  # Labor Day
        dt.date(2026, 11, 26),  # Thanksgiving
        dt.date(2026, 12, 25),  # Christmas
    }
)

NYSE_HOLIDAYS_2027: frozenset[dt.date] = frozenset(
    {
        dt.date(2027, 1, 1),  # New Year's Day
        dt.date(2027, 1, 18),  # MLK Day
        dt.date(2027, 2, 15),  # Washington's Birthday
        dt.date(2027, 3, 26),  # Good Friday
        dt.date(2027, 5, 31),  # Memorial Day
        dt.date(2027, 6, 18),  # Juneteenth (observed)
        dt.date(2027, 7, 5),  # Independence Day (observed)
        dt.date(2027, 9, 6),  # Labor Day
        dt.date(2027, 11, 25),  # Thanksgiving
        dt.date(2027, 12, 24),  # Christmas (observed)
    }
)

NYSE_HOLIDAYS: frozenset[dt.date] = NYSE_HOLIDAYS_2026 | NYSE_HOLIDAYS_2027


def market_today() -> dt.date:
    return dt.datetime.now(ZoneInfo(MARKET_TIMEZONE)).date()


def is_trading_day(date: dt.date) -> bool:
    return date.weekday() < 5 and date not in NYSE_HOLIDAYS


def next_trading_day(date: dt.date) -> dt.date:
    """The next trading day strictly after `date`."""
    candidate = date + dt.timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += dt.timedelta(days=1)
    return candidate


def add_trading_days(start: dt.date, n: int) -> dt.date:
    """The date reached by stepping forward `n` trading days from `start`.
    `start` itself is never counted, even when it is itself a trading day."""
    result = start
    for _ in range(n):
        result = next_trading_day(result)
    return result


def trading_days_between(start: dt.date, end: dt.date) -> int:
    """Number of trading days strictly after `start`, up to and including
    `end`. Zero if `end` <= `start`. Walks calendar day by day rather than
    trading-day by trading-day, so it never overshoots a non-trading `end`
    (e.g. counting a Saturday `end` must not jump past it to Monday)."""
    count = 0
    current = start
    while current < end:
        current += dt.timedelta(days=1)
        if is_trading_day(current):
            count += 1
    return count


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = ""
    runtime_model: str = "claude-sonnet-5"

    # Adapter selection only. The adapter's own connection settings and
    # credentials are read from env inside src/gateway/adapters/ (CLAUDE.md
    # rule 3), never surfaced here.
    adapter: AdapterName = "robinhood"


def get_settings() -> Settings:
    return Settings()
