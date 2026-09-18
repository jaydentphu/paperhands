"""FastAPI app: read endpoints only (Stage 7). Every number here was
already computed by src/validator, src/portfolio, or src/evaluator and is
just being read back from the database - this process never touches the
gateway, the agent, or the Anthropic API.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.schemas import DecisionOut, LogOut, MetricsOut, PositionOut, RunOut
from src.config import market_today
from src.evaluator import CohortMetrics, cohort_metrics
from src.evaluator.evaluate import CONTRACT_MULTIPLIER
from src.models import Decision, Evaluation, Mark, PaperPosition, Run, RunLog
from src.models.db import get_sessionmaker
from src.models.enums import Cohort, PositionStatus

app = FastAPI(title="Options Research & Evaluation Agent")

# Dashboard has no auth (PRD section 5, out of scope) and is personal/
# local-only, but the browser still enforces CORS between the Vite dev
# server (5173) and this API (8000) - and between the built app served
# by the frontend container (3000) and this API. Scoped to those two
# known local origins, not a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_sessionmaker = get_sessionmaker()


def get_db() -> Iterator[Session]:
    with _sessionmaker() as session:
        yield session


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _run_out(run: Run) -> RunOut:
    return RunOut(
        id=run.id,
        run_date=run.run_date,
        status=run.status.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _decision_out(d: Decision) -> DecisionOut:
    return DecisionOut(
        id=d.id,
        run_id=d.run_id,
        cohort=d.cohort.value,
        ticker=d.ticker,
        action=d.action.value,
        contract_id=d.contract_id,
        reasoning=d.reasoning,
        confidence=d.confidence,
        validator_status=d.validator_status.value,
        rejection_reason=d.rejection_reason,
        created_at=d.created_at,
    )


def _unrealized_pnl(position: PaperPosition, mark_price: Decimal | None) -> Decimal | None:
    """Same formula as evaluate_position's realized case, applied to a
    still-open position's latest recorded Mark instead of its close_price."""
    if position.status != PositionStatus.OPEN or mark_price is None:
        return None
    return (mark_price - position.open_price) * CONTRACT_MULTIPLIER * position.quantity


def _position_out(
    p: PaperPosition, ticker: str, mark_price: Decimal | None, realized_pnl: Decimal | None
) -> PositionOut:
    unrealized = _unrealized_pnl(p, mark_price)
    return PositionOut(
        id=p.id,
        cohort=p.cohort.value,
        decision_id=p.decision_id,
        ticker=ticker,
        contract_id=p.contract_id,
        expiry=p.expiry,
        opened_at=p.opened_at,
        open_price=str(p.open_price),
        underlying_open=str(p.underlying_open),
        underlying_close=str(p.underlying_close) if p.underlying_close is not None else None,
        quantity=p.quantity,
        max_loss=str(p.max_loss),
        status=p.status.value,
        closed_at=p.closed_at,
        close_price=str(p.close_price) if p.close_price is not None else None,
        close_reason=p.close_reason.value if p.close_reason is not None else None,
        mark_price=str(mark_price) if mark_price is not None else None,
        unrealized_pnl=str(unrealized) if unrealized is not None else None,
        realized_pnl=str(realized_pnl) if realized_pnl is not None else None,
    )


def _log_out(log: RunLog) -> LogOut:
    return LogOut(
        id=log.id,
        run_id=log.run_id,
        level=log.level.value,
        component=log.component,
        message=log.message,
        payload=log.payload,
        created_at=log.created_at,
    )


def _metrics_out(m: CohortMetrics) -> MetricsOut:
    return MetricsOut(
        cohort=m.cohort.value,
        start=m.start,
        end=m.end,
        decisions=m.decisions,
        no_trade_count=m.no_trade_count,
        trades=m.trades,
        hit_rate=str(m.hit_rate),
        mean_pnl=str(m.mean_pnl),
        median_pnl=str(m.median_pnl),
        total_pnl=str(m.total_pnl),
        max_drawdown=str(m.max_drawdown),
        pnl_vs_cash=str(m.pnl_vs_cash),
    )


@app.get("/runs/latest", response_model=RunOut)
def latest_run(db: Session = Depends(get_db)) -> RunOut:
    run = db.scalar(select(Run).order_by(Run.run_date.desc(), Run.id.desc()))
    if run is None:
        raise HTTPException(status_code=404, detail="no runs found")
    return _run_out(run)


@app.get("/decisions", response_model=list[DecisionOut])
def list_decisions(
    date: dt.date | None = Query(default=None), db: Session = Depends(get_db)
) -> list[DecisionOut]:
    target_date = date or db.scalar(select(func.max(Run.run_date)))
    if target_date is None:
        return []
    rows = db.scalars(
        select(Decision)
        .join(Run, Run.id == Decision.run_id)
        .where(Run.run_date == target_date)
        .order_by(Decision.cohort, Decision.ticker)
    ).all()
    return [_decision_out(d) for d in rows]


@app.get("/positions", response_model=list[PositionOut])
def list_positions(
    status: PositionStatus | None = Query(default=None), db: Session = Depends(get_db)
) -> list[PositionOut]:
    latest_mark = (
        select(Mark.bid)
        .where(Mark.position_id == PaperPosition.id)
        .order_by(Mark.mark_date.desc())
        .limit(1)
        .correlate(PaperPosition)
        .scalar_subquery()
    )
    stmt = (
        select(PaperPosition, Decision.ticker, latest_mark, Evaluation.realized_pnl)
        .join(Decision, Decision.id == PaperPosition.decision_id)
        .outerjoin(Evaluation, Evaluation.position_id == PaperPosition.id)
        .order_by(PaperPosition.opened_at.desc())
    )
    if status is not None:
        stmt = stmt.where(PaperPosition.status == status)
    rows = db.execute(stmt).all()
    return [_position_out(p, ticker, mark, pnl) for p, ticker, mark, pnl in rows]


@app.get("/metrics", response_model=list[MetricsOut])
def list_metrics(
    cohort: Cohort | None = Query(default=None),
    start: dt.date | None = Query(default=None),
    end: dt.date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MetricsOut]:
    lo, hi = db.execute(select(func.min(Run.run_date), func.max(Run.run_date))).one()
    default_day = market_today()
    window_start = start or lo or default_day
    window_end = end or hi or default_day
    cohorts = [cohort] if cohort is not None else [Cohort.A, Cohort.B, Cohort.C]
    return [_metrics_out(cohort_metrics(db, c, window_start, window_end)) for c in cohorts]


@app.get("/logs", response_model=list[LogOut])
def list_logs(
    run_id: int | None = Query(default=None), db: Session = Depends(get_db)
) -> list[LogOut]:
    target_run_id = run_id or db.scalar(select(func.max(Run.id)))
    if target_run_id is None:
        return []
    rows = db.scalars(
        select(RunLog).where(RunLog.run_id == target_run_id).order_by(RunLog.id)
    ).all()
    return [_log_out(r) for r in rows]
