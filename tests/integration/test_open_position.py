"""Real-DB tests for open_position - it needs a real Session for the
"already open for this ticker" existence query, so these live alongside
the other integration tests rather than being mocked at the unit level.

Also satisfies Stage 5's own "Done when": a position opened from a
Stage-4-shaped candidate appears in paper_positions with max_loss = ask x 100.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from src.gateway import DataGateway
from src.gateway.types import Bar, Headline, OptionContract, Quote
from src.models import Decision, PaperPosition, Run, WatchlistSymbol
from src.models.enums import Action, ContractType, PositionStatus, RunStatus, ValidatorStatus
from src.models.enums import Cohort as CohortEnum
from src.portfolio.open import (
    CONTRACT_NOT_FOUND,
    POSITION_ALREADY_OPEN,
    Opened,
    Rejected,
    open_position,
)

TODAY = dt.date(2026, 1, 12)


class StubAdapter:
    def __init__(self, chain: list[OptionContract]) -> None:
        self._chain = chain

    def get_quote(self, ticker: str) -> Quote:
        last = Decimal("150.00")
        return Quote(
            ticker=ticker,
            last=last,
            bid=last,
            ask=last,
            previous_close=last,
            as_of=dt.datetime.combine(TODAY, dt.time(10, 30), tzinfo=dt.UTC),
        )

    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]:
        return self._chain

    def get_historicals(self, ticker: str, days: int) -> list[Bar]:
        raise NotImplementedError

    def get_earnings_date(self, ticker: str) -> dt.date | None:
        raise NotImplementedError

    def get_news(self, ticker: str, limit: int) -> list[Headline]:
        raise NotImplementedError


def _contract(**overrides: object) -> OptionContract:
    base: dict[str, object] = dict(
        contract_id="c-1",
        ticker="ZTEST1",
        contract_type=ContractType.CALL,
        strike=Decimal("150"),
        expiry=dt.date(2026, 2, 20),
        bid=Decimal("2.20"),
        ask=Decimal("2.30"),  # spread 4.4% of mid, under the 5% eligibility cap
        volume=100,
        open_interest=1000,
        implied_vol=Decimal("0.3"),
    )
    base.update(overrides)
    return OptionContract(**base)  # type: ignore[arg-type]


def _seed_decision(session: Session, **overrides: object) -> Decision:
    if session.get(WatchlistSymbol, "ZTEST1") is None:
        session.add(WatchlistSymbol(ticker="ZTEST1"))
    run = Run(run_date=TODAY, status=RunStatus.RUNNING)
    session.add(run)
    session.flush()

    fields: dict[str, object] = dict(
        run_id=run.id,
        cohort=CohortEnum.C,
        ticker="ZTEST1",
        action=Action.LONG_CALL,
        contract_id="c-1",
        reasoning={"thesis": "test"},
        confidence=0.6,
        validator_status=ValidatorStatus.ACCEPTED,
        rejection_reason=None,
    )
    fields.update(overrides)
    decision = Decision(**fields)  # type: ignore[arg-type]
    session.add(decision)
    session.flush()
    return decision


def test_position_from_a_candidate_appears_in_paper_positions_with_max_loss_ask_x_100(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        decision = _seed_decision(session)
        gateway = DataGateway(StubAdapter([_contract()]))

        result = open_position(session, gateway, decision, as_of=TODAY)
        session.commit()

        assert isinstance(result, Opened)
        position_id = result.position.id

    with db_session_factory() as session:
        stored = session.get(PaperPosition, position_id)
        assert stored is not None
        assert stored.open_price == Decimal("2.30")
        assert stored.max_loss == Decimal("230.00")
        assert stored.quantity == 1
        assert stored.status == PositionStatus.OPEN
        assert stored.expiry == dt.date(2026, 2, 20)


def test_open_position_rejected_when_contract_missing_from_live_chain(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        decision = _seed_decision(session)
        gateway = DataGateway(StubAdapter([]))
        result = open_position(session, gateway, decision, as_of=TODAY)
        assert result == Rejected(CONTRACT_NOT_FOUND)


def test_open_position_rejected_when_ineligible_at_fill_time(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        decision = _seed_decision(session)
        gateway = DataGateway(StubAdapter([_contract(open_interest=100)]))
        result = open_position(session, gateway, decision, as_of=TODAY)
        assert isinstance(result, Rejected)
        assert result.reason == "open_interest_too_low"


def test_open_position_rejected_when_position_already_open_for_ticker(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        first_decision = _seed_decision(session)
        gateway = DataGateway(StubAdapter([_contract()]))
        first = open_position(session, gateway, first_decision, as_of=TODAY)
        assert isinstance(first, Opened)

        second_decision = _seed_decision(session, contract_id="c-2")
        second = open_position(
            session, gateway, second_decision, as_of=TODAY + dt.timedelta(days=1)
        )
        assert second == Rejected(POSITION_ALREADY_OPEN)
