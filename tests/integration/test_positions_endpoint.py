"""GET /positions: the ticker/mark_price/unrealized_pnl/realized_pnl joins
added in Stage 8b (see NOTES.md) - not covered by test_daily_run.py, which
only checks position creation, not the read endpoint's shape.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app, get_db
from src.models import Decision, Evaluation, Mark, PaperPosition, Run, WatchlistSymbol
from src.models.enums import (
    Action,
    CloseReason,
    Cohort,
    PositionStatus,
    RunStatus,
    ValidatorStatus,
)

OPENED = dt.date(2026, 2, 2)


def _run_and_decision(session: Session, ticker: str) -> Decision:
    if session.get(WatchlistSymbol, ticker) is None:
        session.add(WatchlistSymbol(ticker=ticker))
    run = Run(run_date=OPENED, status=RunStatus.RUNNING)
    session.add(run)
    session.flush()
    decision = Decision(
        run_id=run.id,
        cohort=Cohort.C,
        ticker=ticker,
        action=Action.LONG_CALL,
        contract_id="c-open",
        reasoning=None,
        confidence=0.6,
        validator_status=ValidatorStatus.ACCEPTED,
        rejection_reason=None,
    )
    session.add(decision)
    session.flush()
    return decision


def test_open_position_reports_ticker_and_latest_mark_as_unrealized_pnl(
    db_session: Session,
) -> None:
    decision = _run_and_decision(db_session, "ZTEST1")
    position = PaperPosition(
        cohort=Cohort.C,
        decision_id=decision.id,
        contract_id="c-open",
        expiry=dt.date(2026, 6, 1),
        opened_at=dt.datetime.combine(OPENED, dt.time(10, 30), tzinfo=dt.UTC),
        open_price=Decimal("2.50"),
        underlying_open=Decimal("200.00"),
        quantity=1,
        max_loss=Decimal("250.00"),
        status=PositionStatus.OPEN,
    )
    db_session.add(position)
    db_session.flush()
    # Two Mark rows on different dates - the endpoint must return the
    # latest one, not the first or an arbitrary one.
    db_session.add(Mark(position_id=position.id, mark_date=OPENED, bid=Decimal("2.60")))
    db_session.add(
        Mark(
            position_id=position.id,
            mark_date=OPENED + dt.timedelta(days=1),
            bid=Decimal("3.30"),
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        rows = client.get("/positions", params={"status": "open"}).json()
    finally:
        app.dependency_overrides.clear()

    row = next(r for r in rows if r["id"] == position.id)
    assert row["ticker"] == "ZTEST1"
    # Money columns are NUMERIC(12,4) - round-trips at 4 decimal places,
    # same as every other money field this API returns (see open_price in
    # PositionOut), not rounded to cents.
    assert row["mark_price"] == "3.3000"
    assert row["unrealized_pnl"] == "80.0000"
    assert row["realized_pnl"] is None


def test_open_position_without_a_mark_yet_has_null_mark_and_unrealized(
    db_session: Session,
) -> None:
    decision = _run_and_decision(db_session, "ZTEST1")
    position = PaperPosition(
        cohort=Cohort.C,
        decision_id=decision.id,
        contract_id="c-nomark",
        expiry=dt.date(2026, 6, 1),
        opened_at=dt.datetime.combine(OPENED, dt.time(10, 30), tzinfo=dt.UTC),
        open_price=Decimal("2.50"),
        underlying_open=Decimal("200.00"),
        quantity=1,
        max_loss=Decimal("250.00"),
        status=PositionStatus.OPEN,
    )
    db_session.add(position)
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        rows = client.get("/positions", params={"status": "open"}).json()
    finally:
        app.dependency_overrides.clear()

    row = next(r for r in rows if r["id"] == position.id)
    assert row["mark_price"] is None
    assert row["unrealized_pnl"] is None


def test_closed_position_reports_realized_pnl_and_no_unrealized(db_session: Session) -> None:
    decision = _run_and_decision(db_session, "ZTEST1")
    position = PaperPosition(
        cohort=Cohort.C,
        decision_id=decision.id,
        contract_id="c-closed",
        expiry=dt.date(2026, 6, 1),
        opened_at=dt.datetime.combine(OPENED, dt.time(10, 30), tzinfo=dt.UTC),
        open_price=Decimal("2.00"),
        underlying_open=Decimal("200.00"),
        underlying_close=Decimal("206.00"),
        quantity=1,
        max_loss=Decimal("200.00"),
        status=PositionStatus.CLOSED,
        closed_at=dt.datetime.combine(
            OPENED + dt.timedelta(days=7), dt.time(16, 15), tzinfo=dt.UTC
        ),
        close_price=Decimal("2.80"),
        close_reason=CloseReason.HORIZON,
    )
    db_session.add(position)
    db_session.flush()
    db_session.add(
        Evaluation(
            position_id=position.id,
            realized_pnl=Decimal("80.00"),
            direction_correct=True,
            horizon_days=5,
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        rows = client.get("/positions", params={"status": "closed"}).json()
    finally:
        app.dependency_overrides.clear()

    row = next(r for r in rows if r["id"] == position.id)
    assert row["ticker"] == "ZTEST1"
    assert row["realized_pnl"] == "80.0000"
    assert row["unrealized_pnl"] is None
