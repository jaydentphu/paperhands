"""Live contract lookups shared by open/mark/close.

A position's remaining DTE at mark/close time is well below what it was at
open, so a wide window (not the eligibility window) is used to make sure
the contract is still found regardless of how much time has passed.
"""

from __future__ import annotations

from src.gateway import DataGateway
from src.gateway.types import OptionContract

WIDE_MIN_DTE = 0
WIDE_MAX_DTE = 400


def fetch_chain_lookup(gateway: DataGateway, ticker: str) -> dict[str, OptionContract]:
    """A ticker's full option chain, keyed by contract_id. One gateway call
    per ticker - callers should reuse this across every position on the
    same ticker rather than calling per-position."""
    contracts = gateway.get_option_chain(ticker, WIDE_MIN_DTE, WIDE_MAX_DTE)
    return {c.contract_id: c for c in contracts}
