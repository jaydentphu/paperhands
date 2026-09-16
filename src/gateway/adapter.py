"""The adapter interface: the five read methods from PRD.md section 7.
Every data source (Robinhood MCP, fake) implements exactly this."""

from __future__ import annotations

import datetime as dt
from typing import Protocol

from src.gateway.types import Bar, Headline, OptionContract, Quote


class Adapter(Protocol):
    def get_quote(self, ticker: str) -> Quote: ...

    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]: ...

    def get_historicals(self, ticker: str, days: int) -> list[Bar]: ...

    def get_earnings_date(self, ticker: str) -> dt.date | None: ...

    def get_news(self, ticker: str, limit: int) -> list[Headline]: ...
