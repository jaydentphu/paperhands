"""Runs daily_run with a fully scripted adapter (guarantees Cohort B a
bullish signal and one clean eligible contract) and a mocked LLM (always
answers no_trade), and asserts one decision per cohort per ticker and
correct position creation.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from typing import Any

from anthropic.types import Message
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.gateway import DataGateway
from src.gateway.types import Bar, Headline, OptionContract, Quote
from src.models import Decision, PaperPosition
from src.models.enums import Action, Cohort, PositionStatus, ValidatorStatus
from src.scheduler.daily_run import run_daily

TODAY = dt.date(2026, 1, 12)
# Must be real watchlist tickers, not synthetic test ones: Cohort C's real
# validate_candidate() rejects any ticker outside WATCHLIST unconditionally
# (PRD section 6 - true even for a no_trade candidate), and this test
# exercises that real path, not a stub of it.
TICKERS = ("AAPL", "MSFT")


class _ScriptedAdapter:
    """A single clean, comfortably-eligible near-ATM call per ticker, and a
    strong uptrend in historicals - guarantees Cohort B fires long_call
    deterministically, regardless of FakeAdapter-style randomness."""

    def __init__(self, today: dt.date) -> None:
        self.today = today

    def get_quote(self, ticker: str) -> Quote:
        last = Decimal("100.00")
        return Quote(
            ticker=ticker,
            last=last,
            bid=last,
            ask=last,
            previous_close=last,
            as_of=dt.datetime.combine(self.today, dt.time(10, 30), tzinfo=dt.UTC),
        )

    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]:
        return [
            OptionContract(
                contract_id=f"{ticker}-CALL-35",
                ticker=ticker,
                contract_type="call",
                strike=Decimal("100"),
                expiry=self.today + dt.timedelta(days=35),
                bid=Decimal("2.00"),
                ask=Decimal("2.10"),
                volume=100,
                open_interest=1000,
                implied_vol=Decimal("0.3"),
            )
        ]

    def get_historicals(self, ticker: str, days: int) -> list[Bar]:
        return [
            Bar(
                date=self.today - dt.timedelta(days=days - i),
                open=Decimal(100 + i),
                high=Decimal(100 + i),
                low=Decimal(100 + i),
                close=Decimal(100 + i),
                volume=1_000_000,
            )
            for i in range(days)
        ]

    def get_earnings_date(self, ticker: str) -> dt.date | None:
        return None

    def get_news(self, ticker: str, limit: int) -> list[Headline]:
        return [
            Headline(
                title=f"{ticker} headline",
                publisher="Wire",
                published_at=dt.datetime.combine(self.today, dt.time(9, 0), tzinfo=dt.UTC),
            )
        ]


class _NoTradeMessages:
    """A mocked LLM that always answers no_trade for whichever ticker is
    named in the bundle - Cohort B alone is enough to prove position
    creation, so this keeps Cohort C's mock simple."""

    def create(self, **kwargs: Any) -> Message:
        user_text = kwargs["messages"][0]["content"]
        ticker = user_text.split("TICKER: ")[1].split("\n")[0].strip()
        payload = json.dumps(
            {
                "ticker": ticker,
                "action": "no_trade",
                "contract_id": None,
                "thesis": "No strong edge in this bundle today.",
                "evidence_for": ["Return is modest", "No major catalyst"],
                "evidence_against": ["Some volatility", "Earnings risk"],
                "confidence": 0.5,
                "invalidation": "A sharp move in either direction.",
            }
        )
        return Message.model_validate(
            {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": payload}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
        )


def test_daily_run_creates_one_decision_per_cohort_and_opens_a_position(
    db_session_factory: sessionmaker[Session],
) -> None:
    gateway = DataGateway(_ScriptedAdapter(TODAY))
    messages = _NoTradeMessages()

    result = run_daily(db_session_factory, gateway, messages, TICKERS, TODAY, "claude-sonnet-5")

    assert [cr.cohort for cr in result.cohort_results] == [Cohort.A, Cohort.B, Cohort.C]
    assert all(not cr.failed for cr in result.cohort_results)
    assert all(cr.tickers_processed == len(TICKERS) for cr in result.cohort_results)
    assert result.snapshot_failed == []

    with db_session_factory() as session:
        decisions = session.scalars(
            select(Decision).where(Decision.run_id == result.run_id)
        ).all()
        assert len(decisions) == len(TICKERS) * 3
        for cohort in (Cohort.A, Cohort.B, Cohort.C):
            assert sum(1 for d in decisions if d.cohort == cohort) == len(TICKERS)

        a_decisions = [d for d in decisions if d.cohort == Cohort.A]
        assert all(d.action == Action.NO_TRADE for d in a_decisions)

        b_decisions = [d for d in decisions if d.cohort == Cohort.B]
        assert all(d.action == Action.LONG_CALL for d in b_decisions)
        assert all(d.validator_status == ValidatorStatus.ACCEPTED for d in b_decisions)
        assert {d.contract_id for d in b_decisions} == {f"{t}-CALL-35" for t in TICKERS}

        c_decisions = [d for d in decisions if d.cohort == Cohort.C]
        assert all(d.action == Action.NO_TRADE for d in c_decisions)
        assert all(d.validator_status == ValidatorStatus.ACCEPTED for d in c_decisions)

        # Scoped to this test's own run_id throughout - the database may
        # already hold other positions (real usage, other tests), and
        # PaperPosition itself has no run_id column (only decision_id), so
        # every query here joins through Decision to filter correctly.
        def _positions_for(cohort: Cohort) -> list[PaperPosition]:
            return list(
                session.scalars(
                    select(PaperPosition)
                    .join(Decision, Decision.id == PaperPosition.decision_id)
                    .where(Decision.run_id == result.run_id, PaperPosition.cohort == cohort)
                ).all()
            )

        b_positions = _positions_for(Cohort.B)
        assert len(b_positions) == len(TICKERS)
        for p in b_positions:
            assert p.status == PositionStatus.OPEN
            assert p.open_price == Decimal("2.10")
            assert p.max_loss == Decimal("210.00")
            assert p.quantity == 1
            assert p.underlying_open == Decimal("100.00")

        assert _positions_for(Cohort.A) == []
        assert _positions_for(Cohort.C) == []
