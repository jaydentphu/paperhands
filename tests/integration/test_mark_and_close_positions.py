"""Fixtures with known bid/ask sequences proving: mark at bid, the
zero-bid case, close at horizon (crossing both a weekend and a listed
holiday), and close 2 trading days before expiry.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.gateway import DataGateway
from src.gateway.types import Bar, Headline, OptionContract, Quote
from src.models import Decision, Mark, PaperPosition, Run, WatchlistSymbol
from src.models.enums import (
    Action,
    Cohort,
    ContractType,
    PositionStatus,
    RunStatus,
    ValidatorStatus,
)
from src.portfolio.close import close_positions
from src.portfolio.mark import mark_positions

# Monday. +5 trading days crosses a weekend (Sat 17/Sun 18) AND MLK Day
# (Mon 19), landing the horizon exit on Tue Jan 20, 2026 - not Fri Jan 16.
OPENED = dt.date(2026, 1, 12)
BEFORE_HORIZON = dt.date(2026, 1, 16)  # only 4 trading days elapsed
EXPIRY = dt.date(2026, 6, 1)  # far enough out to not interact with horizon/pre_expiry logic
AT_HORIZON = dt.date(2026, 1, 20)  # the 5th trading day


class StubAdapter:
    def __init__(self, chain_by_ticker: dict[str, list[OptionContract]]) -> None:
        self._chain_by_ticker = chain_by_ticker

    def get_quote(self, ticker: str) -> Quote:
        last = Decimal("200.00")
        return Quote(
            ticker=ticker,
            last=last,
            bid=last,
            ask=last,
            previous_close=last,
            as_of=dt.datetime.combine(OPENED, dt.time(10, 30), tzinfo=dt.UTC),
        )

    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]:
        return self._chain_by_ticker.get(ticker, [])

    def get_historicals(self, ticker: str, days: int) -> list[Bar]:
        raise NotImplementedError

    def get_earnings_date(self, ticker: str) -> dt.date | None:
        raise NotImplementedError

    def get_news(self, ticker: str, limit: int) -> list[Headline]:
        raise NotImplementedError


def _contract(contract_id: str, ticker: str, bid: Decimal, expiry: dt.date) -> OptionContract:
    return OptionContract(
        contract_id=contract_id,
        ticker=ticker,
        contract_type=ContractType.CALL,
        strike=Decimal("150"),
        expiry=expiry,
        bid=bid,
        ask=bid + Decimal("0.20"),
        volume=100,
        open_interest=1000,
        implied_vol=Decimal("0.3"),
    )


def _seed_position(
    session: Session,
    ticker: str,
    contract_id: str,
    opened_at: dt.date,
    expiry: dt.date,
) -> PaperPosition:
    if session.get(WatchlistSymbol, ticker) is None:
        session.add(WatchlistSymbol(ticker=ticker))
    run = Run(run_date=opened_at, status=RunStatus.RUNNING)
    session.add(run)
    session.flush()

    decision = Decision(
        run_id=run.id,
        cohort=Cohort.B,
        ticker=ticker,
        action=Action.LONG_CALL,
        contract_id=contract_id,
        reasoning=None,
        confidence=None,
        validator_status=ValidatorStatus.ACCEPTED,
        rejection_reason=None,
    )
    session.add(decision)
    session.flush()

    position = PaperPosition(
        cohort=Cohort.B,
        decision_id=decision.id,
        contract_id=contract_id,
        expiry=expiry,
        opened_at=dt.datetime.combine(opened_at, dt.time(16, 15), tzinfo=dt.UTC),
        open_price=Decimal("2.00"),
        underlying_open=Decimal("200.00"),
        quantity=1,
        max_loss=Decimal("200.00"),
        status=PositionStatus.OPEN,
    )
    session.add(position)
    session.flush()
    return position


def test_mark_positions_stores_the_bid(db_session_factory: sessionmaker[Session]) -> None:
    with db_session_factory() as session:
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, EXPIRY)
        gateway = DataGateway(
            StubAdapter({"ZTEST1": [_contract("c-1", "ZTEST1", Decimal("2.10"), EXPIRY)]})
        )
        marked = mark_positions(session, gateway, OPENED)
        session.commit()
        # Not asserting an exact count: mark_positions marks every open
        # position system-wide by design, so this must stay correct even
        # when other positions already exist elsewhere in the database.
        assert marked >= 1
        mark = session.scalar(select(Mark).where(Mark.position_id == position.id))
        assert mark is not None
        assert mark.bid == Decimal("2.10")


def test_mark_positions_zero_bid_when_contract_missing_from_chain(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, EXPIRY)
        gateway = DataGateway(StubAdapter({"ZTEST1": []}))
        mark_positions(session, gateway, OPENED)
        session.commit()
        mark = session.scalar(select(Mark).where(Mark.position_id == position.id))
        assert mark is not None
        assert mark.bid == Decimal("0")


def test_mark_positions_is_idempotent_for_the_same_date(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, EXPIRY)
        gateway = DataGateway(
            StubAdapter({"ZTEST1": [_contract("c-1", "ZTEST1", Decimal("2.10"), EXPIRY)]})
        )
        mark_positions(session, gateway, OPENED)
        gateway2 = DataGateway(
            StubAdapter({"ZTEST1": [_contract("c-1", "ZTEST1", Decimal("1.90"), EXPIRY)]})
        )
        marked_again = mark_positions(session, gateway2, OPENED)
        session.commit()

        assert marked_again >= 1
        marks = session.scalars(select(Mark).where(Mark.position_id == position.id)).all()
        assert len(marks) == 1
        assert marks[0].bid == Decimal("1.90")


def test_close_positions_does_not_close_before_horizon(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, EXPIRY)
        gateway = DataGateway(
            StubAdapter({"ZTEST1": [_contract("c-1", "ZTEST1", Decimal("2.10"), EXPIRY)]})
        )
        closed = close_positions(session, gateway, BEFORE_HORIZON)
        session.commit()
        assert closed == 0
        session.refresh(position)
        assert position.status == PositionStatus.OPEN


def test_close_positions_closes_at_horizon_across_weekend_and_holiday(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, EXPIRY)
        gateway = DataGateway(
            StubAdapter({"ZTEST1": [_contract("c-1", "ZTEST1", Decimal("1.75"), EXPIRY)]})
        )
        closed = close_positions(session, gateway, AT_HORIZON)
        session.commit()

        assert closed == 1
        session.refresh(position)
        assert position.status == PositionStatus.CLOSED
        assert position.close_price == Decimal("1.75")
        assert position.close_reason.value == "horizon"


def test_close_positions_zero_bid_when_contract_missing(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, EXPIRY)
        gateway = DataGateway(StubAdapter({"ZTEST1": []}))
        close_positions(session, gateway, AT_HORIZON)
        session.commit()
        session.refresh(position)
        assert position.status == PositionStatus.CLOSED
        assert position.close_price == Decimal("0")


def test_close_positions_closes_two_trading_days_before_expiry(
    db_session_factory: sessionmaker[Session],
) -> None:
    # Short-dated on purpose to trigger pre_expiry before the 5-day horizon
    # would. Opened Mon Jan 12, expires Thu Jan 15.
    with db_session_factory() as session:
        expiry = dt.date(2026, 1, 15)
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, expiry)
        gateway = DataGateway(
            StubAdapter({"ZTEST1": [_contract("c-1", "ZTEST1", Decimal("1.10"), expiry)]})
        )

        # Tue Jan 13: 1 trading day since open (not horizon), 2 trading
        # days to expiry (Wed 14, Thu 15) -> pre_expiry.
        closed = close_positions(session, gateway, dt.date(2026, 1, 13))
        session.commit()

        assert closed == 1
        session.refresh(position)
        assert position.status == PositionStatus.CLOSED
        assert position.close_reason.value == "pre_expiry"
        assert position.close_price == Decimal("1.10")


def test_close_positions_leaves_position_open_before_horizon_or_pre_expiry(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        expiry = dt.date(2026, 1, 15)
        position = _seed_position(session, "ZTEST1", "c-1", OPENED, expiry)
        gateway = DataGateway(
            StubAdapter({"ZTEST1": [_contract("c-1", "ZTEST1", Decimal("1.10"), expiry)]})
        )
        # Same day as open: 0 trading days elapsed, 3 trading days to
        # expiry (Tue13, Wed14, Thu15) - neither trigger fires.
        closed = close_positions(session, gateway, OPENED)
        session.commit()
        assert closed == 0
        session.refresh(position)
        assert position.status == PositionStatus.OPEN
