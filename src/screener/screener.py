"""Cohort B: a documented, deterministic rule set.

Rule (thresholds are a build-time choice, not from the PRD - see NOTES.md
Stage 4 "Strategy v1 revision" for the tuning rationale):
  bullish  if 20-day return > +3% AND 14-day RSI > 55  -> long_call
  bearish  if 20-day return < -3% AND 14-day RSI < 45  -> long_put
  otherwise                                             -> no_trade

Contract selection, when a direction is chosen: among eligible contracts of
the matching type AND within MONEYNESS_CAP_PCT of the spot price, pick the
one closest to TARGET_DTE, breaking ties by closeness to at-the-money. If
nothing is within the moneyness cap, the result is no_trade - the strike is
never allowed to drift OTM just because a cheaper contract happens to
satisfy the eligibility filter's premium cap.

No trade if earnings falls within the horizon: if a signal fires but
earnings is scheduled between now and the horizon exit date (inclusive),
the result is no_trade regardless of direction - deferred from the Stage 4
strategy review until this stage's trading-day calendar existed to compute
the horizon exit date correctly (see NOTES.md).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from src.config import HORIZON_DAYS, add_trading_days
from src.gateway.types import Bar
from src.models import ContractSnapshot
from src.models.enums import Action, ContractType
from src.screener.indicators import rsi_14, twenty_day_return

BULLISH_RETURN = Decimal("0.03")
BEARISH_RETURN = Decimal("-0.03")
BULLISH_RSI = Decimal(55)
BEARISH_RSI = Decimal(45)
TARGET_DTE = 35
MONEYNESS_CAP_PCT = Decimal("0.02")

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
    earnings_date: dt.date | None = None,
) -> ScreenerDecision:
    ret = twenty_day_return(bars)
    rsi = rsi_14(bars)

    if ret > BULLISH_RETURN and rsi > BULLISH_RSI:
        action = Action.LONG_CALL
    elif ret < BEARISH_RETURN and rsi < BEARISH_RSI:
        action = Action.LONG_PUT
    else:
        return ScreenerDecision(Action.NO_TRADE, None)

    if earnings_date is not None:
        horizon_exit = add_trading_days(as_of, HORIZON_DAYS)
        if as_of <= earnings_date <= horizon_exit:
            return ScreenerDecision(Action.NO_TRADE, None)

    wanted_type = _ACTION_CONTRACT_TYPE[action]
    max_distance = spot * MONEYNESS_CAP_PCT
    candidates = [
        c
        for c in eligible_contracts
        if c.contract_type == wanted_type and abs(c.strike - spot) <= max_distance
    ]
    if not candidates:
        return ScreenerDecision(Action.NO_TRADE, None)

    def distance(contract: ContractSnapshot) -> tuple[int, Decimal]:
        dte = (contract.expiry - as_of).days
        return (abs(dte - TARGET_DTE), abs(contract.strike - spot))

    return ScreenerDecision(action, min(candidates, key=distance))
