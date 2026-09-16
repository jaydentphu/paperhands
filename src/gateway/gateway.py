"""DataGateway: the only surface the research agent ever touches.

It exposes the five ALLOWLIST functions and nothing else. There is no
generic dispatch; every function is a named method, each tagged
is_mutating = False. Any other attribute lookup raises CapabilityError.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from typing import NoReturn

from src.gateway.adapter import Adapter
from src.gateway.allowlist import ALLOWLIST, CapabilityError
from src.gateway.types import Bar, Headline, OptionContract, Quote


def read_only[F: Callable[..., object]](fn: F) -> F:
    fn.__dict__["is_mutating"] = False
    return fn


class DataGateway:
    __slots__ = ("_adapter",)

    def __init__(self, adapter: Adapter) -> None:
        self._adapter = adapter

    @read_only
    def get_quote(self, ticker: str) -> Quote:
        return self._adapter.get_quote(ticker)

    @read_only
    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]:
        return self._adapter.get_option_chain(ticker, min_dte, max_dte)

    @read_only
    def get_historicals(self, ticker: str, days: int) -> list[Bar]:
        return self._adapter.get_historicals(ticker, days)

    @read_only
    def get_earnings_date(self, ticker: str) -> dt.date | None:
        return self._adapter.get_earnings_date(ticker)

    @read_only
    def get_news(self, ticker: str, limit: int) -> list[Headline]:
        return self._adapter.get_news(ticker, limit)

    def tools(self) -> tuple[Callable[..., object], ...]:
        """The bound functions handed to the agent, in ALLOWLIST order."""
        return tuple(getattr(self, name) for name in ALLOWLIST)

    def __getattr__(self, name: str) -> NoReturn:
        if name.startswith("__"):
            raise AttributeError(name)
        raise CapabilityError(name)


for _name in ALLOWLIST:
    assert getattr(DataGateway, _name).is_mutating is False
