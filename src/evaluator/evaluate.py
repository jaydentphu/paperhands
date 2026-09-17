"""Per-position scoring, written once when a position closes.

realized_pnl      = (close_price - open_price) x 100 x quantity
direction_correct = the underlying moved in the thesis direction between
                    open and close (strictly; unchanged counts as wrong)
horizon_days      = trading days actually held
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import trading_days_between
from src.models import Decision, Evaluation, PaperPosition
from src.models.enums import Action, PositionStatus

CONTRACT_MULTIPLIER = 100


def evaluate_position(position: PaperPosition, action: Action) -> Evaluation:
    if (
        position.close_price is None
        or position.closed_at is None
        or position.underlying_close is None
    ):
        raise ValueError(f"position {position.id} is not closed with a recorded underlying")

    per_contract = position.close_price - position.open_price
    realized = per_contract * CONTRACT_MULTIPLIER * position.quantity
    if action == Action.LONG_CALL:
        correct = position.underlying_close > position.underlying_open
    elif action == Action.LONG_PUT:
        correct = position.underlying_close < position.underlying_open
    else:
        raise ValueError(f"position {position.id} has a no_trade decision")

    return Evaluation(
        position_id=position.id,
        realized_pnl=Decimal(realized),
        direction_correct=correct,
        horizon_days=trading_days_between(position.opened_at.date(), position.closed_at.date()),
    )


def evaluate_closed_positions(session: Session) -> int:
    """Writes an evaluation row for every closed position that doesn't have
    one yet. Idempotent. Does not commit."""
    rows = session.execute(
        select(PaperPosition, Decision.action)
        .join(Decision, Decision.id == PaperPosition.decision_id)
        .outerjoin(Evaluation, Evaluation.position_id == PaperPosition.id)
        .where(PaperPosition.status == PositionStatus.CLOSED, Evaluation.id.is_(None))
        .order_by(PaperPosition.id)
    ).all()
    for position, action in rows:
        session.add(evaluate_position(position, action))
    session.flush()
    return len(rows)
