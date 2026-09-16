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

# PRD section 4 eligibility defaults.
DTE_MIN: int = 14
DTE_MAX: int = 45
MAX_SPREAD_PCT: Decimal = Decimal("0.10")
MIN_OPEN_INTEREST: int = 500
MAX_PREMIUM: Decimal = Decimal("300.00")

# PRD section 3/4: paper portfolio horizon, in trading days.
HORIZON_DAYS: int = 5

# PRD section 4: one scheduled run per trading day, after market open.
RUN_TIME: dt.time = dt.time(10, 30)
MARK_TIME: dt.time = dt.time(16, 15)
MARKET_TIMEZONE: str = "America/New_York"

# NYSE holiday calendar, hardcoded per CLAUDE.md conventions (no external
# calendar library). Observed dates only; trading-day math lives in
# src/portfolio (Stage 5).
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
