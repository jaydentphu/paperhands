"""Instantiates every model. No DB - just proves each class constructs
with the fields PRD.md/BUILD_STAGES.md Stage 1 specify."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

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
from src.models.base import Base
from src.models.enums import (
    Action,
    Cohort,
    ContractType,
    LogLevel,
    PositionStatus,
    RunStatus,
    ValidatorStatus,
)


def test_watchlist_symbol() -> None:
    row = WatchlistSymbol(ticker="AAPL", active=True)
    assert row.ticker == "AAPL"


def test_run() -> None:
    row = Run(run_date=dt.date(2026, 9, 16), status=RunStatus.RUNNING)
    assert row.status == RunStatus.RUNNING


def test_snapshot() -> None:
    row = Snapshot(
        run_id=1,
        ticker="AAPL",
        quote={"last": "150.00"},
        earnings_date=dt.date(2026, 10, 1),
        news_headlines=["headline one"],
    )
    assert row.ticker == "AAPL"
    assert row.news_headlines == ["headline one"]


def test_contract_snapshot() -> None:
    row = ContractSnapshot(
        snapshot_id=1,
        contract_id="AAPL260101C00150000",
        contract_type=ContractType.CALL,
        strike=Decimal("150.00"),
        expiry=dt.date(2026, 10, 15),
        bid=Decimal("2.10"),
        ask=Decimal("2.30"),
        volume=120,
        open_interest=800,
        implied_vol=Decimal("0.245000"),
        eligible=True,
        ineligible_reason=None,
    )
    assert row.eligible is True


def test_decision() -> None:
    row = Decision(
        run_id=1,
        cohort=Cohort.C,
        ticker="AAPL",
        action=Action.LONG_CALL,
        contract_id="AAPL260101C00150000",
        reasoning={"thesis": "bullish breakout"},
        confidence=0.72,
        validator_status=ValidatorStatus.ACCEPTED,
        rejection_reason=None,
    )
    assert row.cohort == Cohort.C
    assert row.confidence == 0.72


def test_paper_position() -> None:
    row = PaperPosition(
        cohort=Cohort.C,
        decision_id=1,
        contract_id="AAPL260101C00150000",
        opened_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
        open_price=Decimal("2.30"),
        quantity=1,
        max_loss=Decimal("230.00"),
        status=PositionStatus.OPEN,
    )
    assert row.max_loss == Decimal("230.00")


def test_mark() -> None:
    row = Mark(position_id=1, mark_date=dt.date(2026, 9, 17), bid=Decimal("2.05"))
    assert row.bid == Decimal("2.05")


def test_evaluation() -> None:
    row = Evaluation(
        position_id=1,
        realized_pnl=Decimal("-25.00"),
        direction_correct=False,
        horizon_days=5,
    )
    assert row.horizon_days == 5


def test_run_log() -> None:
    row = RunLog(
        run_id=1,
        level=LogLevel.INFO,
        component="gateway",
        message="fetched quote",
        payload={"ticker": "AAPL"},
    )
    assert row.level == LogLevel.INFO


def test_all_nine_tables_registered() -> None:
    expected = {
        "watchlist_symbols",
        "runs",
        "snapshots",
        "contract_snapshots",
        "decisions",
        "paper_positions",
        "marks",
        "evaluations",
        "run_logs",
    }
    assert expected <= set(Base.metadata.tables.keys())
