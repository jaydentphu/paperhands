"""Cohort B: a documented, deterministic rule set.

Rule (thresholds are a build-time choice, not from the PRD - see NOTES.md):
  bullish  if 20-day return > +2% AND 14-day RSI > 55  -> long_call
  bearish  if 20-day return < -2% AND 14-day RSI < 45  -> long_put
  otherwise                                             -> no_trade

Contract selection, when a direction is chosen: among eligible contracts of
the matching type, pick the one closest to 30 DTE, breaking ties by
closeness to at-the-money.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from src.gateway.types import Bar
from src.models import ContractSnapshot
from src.models.enums import Action, ContractType
from src.screener.indicators import rsi_14, twenty_day_return

BULLISH_RETURN = Decimal("0.02")
BEARISH_RETURN = Decimal("-0.02")
BULLISH_RSI = Decimal(55)
BEARISH_RSI = Decimal(45)
TARGET_DTE = 30

_ACTION_CONTRACT_TYPE = {
    Action.LONG_CALL: ContractType.CALL,
    Action.LONG_PUT: ContractType.PUT,
}


@dataclass(frozen=True)
class ScreenerDecision:
    action: Action
    contract: ContractSnapshot | None


def screen(
    bars: list[Bar],
    eligible_contracts: list[ContractSnapshot],
    spot: Decimal,
    as_of: dt.date,
) -> ScreenerDecision:
    ret = twenty_day_return(bars)
    rsi = rsi_14(bars)

    if ret > BULLISH_RETURN and rsi > BULLISH_RSI:
        action = Action.LONG_CALL
    elif ret < BEARISH_RETURN and rsi < BEARISH_RSI:
        action = Action.LONG_PUT
    else:
        return ScreenerDecision(Action.NO_TRADE, None)

    wanted_type = _ACTION_CONTRACT_TYPE[action]
    candidates = [c for c in eligible_contracts if c.contract_type == wanted_type]
    if not candidates:
        return ScreenerDecision(Action.NO_TRADE, None)

    def distance(contract: ContractSnapshot) -> tuple[int, Decimal]:
        dte = (contract.expiry - as_of).days
        return (abs(dte - TARGET_DTE), abs(contract.strike - spot))

    return ScreenerDecision(action, min(candidates, key=distance))
