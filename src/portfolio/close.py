"""close_positions: closes any open position that has reached HORIZON_DAYS
trading days since it opened, or is within 2 trading days of its own
expiry, at the current bid (zero if missing). Horizon is checked first;
pre_expiry is a safety net for whatever slips past it. The underlying's
last price is captured at the same moment for the evaluator.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import HORIZON_DAYS, MARK_TIME, MARKET_TIMEZONE, trading_days_between
from src.gateway import DataGateway
from src.gateway.types import OptionContract
from src.models import Decision, PaperPosition
from src.models.enums import CloseReason, PositionStatus
from src.portfolio.contracts import fetch_chain_lookup

PRE_EXPIRY_TRADING_DAYS = 2


def _close_reason(position: PaperPosition, date: dt.date) -> CloseReason | None:
    opened_date = position.opened_at.date()
    if trading_days_between(opened_date, date) >= HORIZON_DAYS:
        return CloseReason.HORIZON
    if trading_days_between(date, position.expiry) <= PRE_EXPIRY_TRADING_DAYS:
        return CloseReason.PRE_EXPIRY
    return None


def close_positions(session: Session, gateway: DataGateway, date: dt.date) -> int:
    rows = session.execute(
        select(PaperPosition, Decision.ticker)
        .join(Decision, Decision.id == PaperPosition.decision_id)
        .where(PaperPosition.status == PositionStatus.OPEN)
    ).all()

    chains: dict[str, dict[str, OptionContract]] = {}
    underlying: dict[str, Decimal] = {}
    closed = 0
    for position, ticker in rows:
        reason = _close_reason(position, date)
        if reason is None:
            continue

        if ticker not in chains:
            chains[ticker] = fetch_chain_lookup(gateway, ticker)
            underlying[ticker] = gateway.get_quote(ticker).last
        contract = chains[ticker].get(position.contract_id)
        close_price = contract.bid if contract is not None else Decimal("0")

        position.status = PositionStatus.CLOSED
        position.closed_at = dt.datetime.combine(
            date, MARK_TIME, tzinfo=ZoneInfo(MARKET_TIMEZONE)
        )
        position.close_price = close_price
        position.underlying_close = underlying[ticker]
        position.close_reason = reason
        closed += 1

    session.flush()
    return closed
