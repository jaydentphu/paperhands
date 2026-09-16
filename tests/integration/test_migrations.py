"""Applies migrations to the CI Postgres and inserts one row per table."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import (
    ContractSnapshot,
    Decision,
    Evaluation,
    Mark,
    PaperPosition,
    Run,
    RunLog,
    Snapshot,
    WatchlistSymbol,
)
from src.models.enums import (
    Action,
    Cohort,
    ContractType,
    LogLevel,
    PositionStatus,
    RunStatus,
    ValidatorStatus,
)


def test_migration_inserts_one_row_per_table(db_session: Session) -> None:
    watchlist = WatchlistSymbol(ticker="ZTEST", active=True)
    db_session.add(watchlist)
    db_session.flush()

    run = Run(run_date=dt.date(2026, 9, 16), status=RunStatus.COMPLETED)
    db_session.add(run)
    db_session.flush()

    snapshot = Snapshot(
        run_id=run.id,
        ticker=watchlist.ticker,
        quote={"last": "100.00"},
        earnings_date=None,
        news_headlines=[],
    )
    db_session.add(snapshot)
    db_session.flush()

    contract = ContractSnapshot(
        snapshot_id=snapshot.id,
        contract_id="ZTEST260101C00100000",
        contract_type=ContractType.CALL,
        strike=Decimal("100.00"),
        expiry=dt.date(2026, 10, 16),
        bid=Decimal("1.00"),
        ask=Decimal("1.20"),
        volume=10,
        open_interest=600,
        implied_vol=Decimal("0.300000"),
        eligible=True,
        ineligible_reason=None,
    )
    db_session.add(contract)
    db_session.flush()

    decision = Decision(
        run_id=run.id,
        cohort=Cohort.C,
        ticker=watchlist.ticker,
        action=Action.LONG_CALL,
        contract_id=contract.contract_id,
        reasoning={"thesis": "test"},
        confidence=0.5,
        validator_status=ValidatorStatus.ACCEPTED,
        rejection_reason=None,
    )
    db_session.add(decision)
    db_session.flush()

    position = PaperPosition(
        cohort=Cohort.C,
        decision_id=decision.id,
        contract_id=contract.contract_id,
        opened_at=dt.datetime.now(dt.UTC),
        open_price=Decimal("1.20"),
        quantity=1,
        max_loss=Decimal("120.00"),
        status=PositionStatus.OPEN,
    )
    db_session.add(position)
    db_session.flush()

    mark = Mark(position_id=position.id, mark_date=dt.date(2026, 9, 17), bid=Decimal("1.10"))
    db_session.add(mark)

    evaluation = Evaluation(
        position_id=position.id,
        realized_pnl=Decimal("-10.00"),
        direction_correct=False,
        horizon_days=5,
    )
    db_session.add(evaluation)

    log = RunLog(
        run_id=run.id,
        level=LogLevel.INFO,
        component="test",
        message="integration test row",
        payload=None,
    )
    db_session.add(log)
    db_session.flush()

    assert db_session.scalar(select(WatchlistSymbol).where(WatchlistSymbol.ticker == "ZTEST"))
    assert db_session.scalar(select(Run).where(Run.id == run.id))
    assert db_session.scalar(select(Snapshot).where(Snapshot.id == snapshot.id))
    assert db_session.scalar(select(ContractSnapshot).where(ContractSnapshot.id == contract.id))
    assert db_session.scalar(select(Decision).where(Decision.id == decision.id))
    assert db_session.scalar(select(PaperPosition).where(PaperPosition.id == position.id))
    assert db_session.scalar(select(Mark).where(Mark.id == mark.id))
    assert db_session.scalar(select(Evaluation).where(Evaluation.id == evaluation.id))
    assert db_session.scalar(select(RunLog).where(RunLog.id == log.id))
