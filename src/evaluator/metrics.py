"""Per-cohort aggregates over a date window (inclusive, by run_date).

decisions / no_trade_count count decision rows. trades, hit_rate, and the
P&L figures cover positions that have closed and been evaluated - an open
position is not a trade yet. max_drawdown is the largest peak-to-trough
fall of cumulative realized P&L in close order, starting from zero, so a
cohort whose first trade loses shows that loss as drawdown. Cash is the
benchmark and always zero, so pnl_vs_cash == total_pnl.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import Decision, Evaluation, PaperPosition, Run
from src.models.enums import Action, Cohort

CENT = Decimal("0.01")
RATE = Decimal("0.0001")


@dataclass(frozen=True)
class CohortMetrics:
    cohort: Cohort
    start: dt.date
    end: dt.date
    decisions: int
    no_trade_count: int
    trades: int
    hit_rate: Decimal
    mean_pnl: Decimal
    median_pnl: Decimal
    total_pnl: Decimal
    max_drawdown: Decimal
    pnl_vs_cash: Decimal


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def median(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def max_drawdown(pnls_in_close_order: list[Decimal]) -> Decimal:
    peak = Decimal(0)
    cumulative = Decimal(0)
    worst = Decimal(0)
    for pnl in pnls_in_close_order:
        cumulative += pnl
        peak = max(peak, cumulative)
        worst = max(worst, peak - cumulative)
    return worst


def cohort_metrics(session: Session, cohort: Cohort, start: dt.date, end: dt.date) -> CohortMetrics:
    in_window = Run.run_date.between(start, end)

    decisions = session.scalar(
        select(func.count())
        .select_from(Decision)
        .join(Run, Run.id == Decision.run_id)
        .where(Decision.cohort == cohort, in_window)
    )
    no_trades = session.scalar(
        select(func.count())
        .select_from(Decision)
        .join(Run, Run.id == Decision.run_id)
        .where(Decision.cohort == cohort, Decision.action == Action.NO_TRADE, in_window)
    )
    evaluations = session.execute(
        select(Evaluation.realized_pnl, Evaluation.direction_correct)
        .join(PaperPosition, PaperPosition.id == Evaluation.position_id)
        .join(Decision, Decision.id == PaperPosition.decision_id)
        .join(Run, Run.id == Decision.run_id)
        .where(PaperPosition.cohort == cohort, in_window)
        .order_by(PaperPosition.closed_at, PaperPosition.id)
    ).all()

    pnls = [Decimal(pnl) for pnl, _ in evaluations]
    hits = sum(1 for _, correct in evaluations if correct)
    trades = len(pnls)
    total = sum(pnls, Decimal(0))

    return CohortMetrics(
        cohort=cohort,
        start=start,
        end=end,
        decisions=int(decisions or 0),
        no_trade_count=int(no_trades or 0),
        trades=trades,
        hit_rate=(Decimal(hits) / trades).quantize(RATE, rounding=ROUND_HALF_UP)
        if trades
        else Decimal(0),
        mean_pnl=_cents(total / trades) if trades else Decimal(0),
        median_pnl=_cents(median(pnls)),
        total_pnl=_cents(total),
        max_drawdown=_cents(max_drawdown(pnls)),
        pnl_vs_cash=_cents(total),
    )
