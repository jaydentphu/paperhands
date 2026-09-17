"""mark_positions: stores today's bid for every open position, zero if the
contract's bid is missing or the contract can no longer be found in the
live chain at all. Idempotent - re-running for the same date updates the
existing Mark row instead of violating its (position_id, mark_date)
unique constraint.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.gateway import DataGateway
from src.gateway.types import OptionContract
from src.models import Decision, Mark, PaperPosition
from src.models.enums import PositionStatus
from src.portfolio.contracts import fetch_chain_lookup


def mark_positions(session: Session, gateway: DataGateway, date: dt.date) -> int:
    rows = session.execute(
        select(PaperPosition, Decision.ticker)
        .join(Decision, Decision.id == PaperPosition.decision_id)
        .where(PaperPosition.status == PositionStatus.OPEN)
    ).all()

    chains: dict[str, dict[str, OptionContract]] = {}
    marked = 0
    for position, ticker in rows:
        if ticker not in chains:
            chains[ticker] = fetch_chain_lookup(gateway, ticker)
        contract = chains[ticker].get(position.contract_id)
        bid = contract.bid if contract is not None else Decimal("0")

        existing = session.scalar(
            select(Mark).where(Mark.position_id == position.id, Mark.mark_date == date)
        )
        if existing is not None:
            existing.bid = bid
        else:
            session.add(Mark(position_id=position.id, mark_date=date, bid=bid))
        marked += 1

    session.flush()
    return marked
