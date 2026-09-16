"""Plain, adapter-independent data types returned by the five gateway
functions. Money is Decimal; JSON views use strings so JSONB columns never
see floats."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

ContractKind = Literal["call", "put"]


@dataclass(frozen=True)
class Quote:
    ticker: str
    last: Decimal
    bid: Decimal
    ask: Decimal
    previous_close: Decimal
    as_of: dt.datetime

    def to_json(self) -> dict[str, str]:
        return {
            "ticker": self.ticker,
            "last": str(self.last),
            "bid": str(self.bid),
            "ask": str(self.ask),
            "previous_close": str(self.previous_close),
            "as_of": self.as_of.isoformat(),
        }


@dataclass(frozen=True)
class OptionContract:
    contract_id: str
    ticker: str
    contract_type: ContractKind
    strike: Decimal
    expiry: dt.date
    bid: Decimal
    ask: Decimal
    volume: int
    open_interest: int
    implied_vol: Decimal | None

    def dte(self, as_of: dt.date) -> int:
        return (self.expiry - as_of).days


@dataclass(frozen=True)
class Bar:
    date: dt.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class Headline:
    title: str
    publisher: str
    published_at: dt.datetime

    def to_json(self) -> dict[str, str]:
        return {
            "title": self.title,
            "publisher": self.publisher,
            "published_at": self.published_at.isoformat(),
        }
