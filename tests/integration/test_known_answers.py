"""Runs the full open -> mark -> close -> evaluate pipeline over
tests/fixtures/known_answers.json (a synthetic March 2026) and asserts every
cohort metric and every per-trade evaluation matches the hand-computed
values in the fixture, to the cent.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.config import is_trading_day
from src.evaluator import cohort_metrics, evaluate_closed_positions
from src.gateway import DataGateway
from src.gateway.types import Bar, Headline, OptionContract, Quote
from src.models import Decision, Evaluation, PaperPosition, Run, Snapshot, WatchlistSymbol
from src.models.enums import Action, Cohort, RunStatus, ValidatorStatus
from src.portfolio import Rejected, close_positions, mark_positions, open_position

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "known_answers.json"


def _load() -> dict[str, Any]:
    with FIXTURE.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


class ScriptedAdapter:
    """Plays the fixture's price tables back for whatever `today` is set to."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self._underlying = fixture["underlying"]
        self._contracts = fixture["contracts"]
        self.today = dt.date.fromisoformat(fixture["start"])

    def _price(self, table: dict[str, Any], key: str | None = None) -> Any:
        override = table["overrides"].get(self.today.isoformat())
        value = override if override is not None else table["default"]
        return value[key] if key else value

    def get_quote(self, ticker: str) -> Quote:
        last = Decimal(self._price(self._underlying[ticker]))
        return Quote(
            ticker=ticker,
            last=last,
            bid=last,
            ask=last,
            previous_close=last,
            as_of=dt.datetime.combine(self.today, dt.time(10, 30), tzinfo=dt.UTC),
        )

    def get_option_chain(self, ticker: str, min_dte: int, max_dte: int) -> list[OptionContract]:
        out = []
        for c in self._contracts:
            if c["ticker"] != ticker:
                continue
            out.append(
                OptionContract(
                    contract_id=c["contract_id"],
                    ticker=ticker,
                    contract_type=c["contract_type"],
                    strike=Decimal(c["strike"]),
                    expiry=dt.date.fromisoformat(c["expiry"]),
                    bid=Decimal(self._price(c, "bid")),
                    ask=Decimal(self._price(c, "ask")),
                    volume=100,
                    open_interest=int(c["open_interest"]),
                    implied_vol=Decimal("0.3"),
                )
            )
        return out

    def get_historicals(self, ticker: str, days: int) -> list[Bar]:
        raise NotImplementedError

    def get_earnings_date(self, ticker: str) -> dt.date | None:
        raise NotImplementedError

    def get_news(self, ticker: str, limit: int) -> list[Headline]:
        raise NotImplementedError


def _trading_days(start: dt.date, end: dt.date) -> list[dt.date]:
    days = []
    day = start
    while day <= end:
        if is_trading_day(day):
            days.append(day)
        day += dt.timedelta(days=1)
    return days


def _run_month(session: Session, fixture: dict[str, Any]) -> list[Rejected]:
    adapter = ScriptedAdapter(fixture)
    gateway = DataGateway(adapter)
    start = dt.date.fromisoformat(fixture["start"])
    end = dt.date.fromisoformat(fixture["end"])
    scripted = {
        (d["date"], d["cohort"], d["ticker"]): d for d in fixture["decisions"]
    }
    for ticker in fixture["tickers"]:
        if session.get(WatchlistSymbol, ticker) is None:
            session.add(WatchlistSymbol(ticker=ticker))
    session.flush()

    unfilled: list[Rejected] = []
    for day in _trading_days(start, end):
        adapter.today = day
        run = Run(run_date=day, status=RunStatus.RUNNING)
        session.add(run)
        session.flush()

        for ticker in fixture["tickers"]:
            quote = adapter.get_quote(ticker)
            session.add(
                Snapshot(
                    run_id=run.id, ticker=ticker, quote=quote.to_json(), news_headlines=[]
                )
            )
            for cohort in (Cohort.A, Cohort.B, Cohort.C):
                script = scripted.get((day.isoformat(), cohort.value, ticker))
                action = Action(script["action"]) if script else Action.NO_TRADE
                decision = Decision(
                    run_id=run.id,
                    cohort=cohort,
                    ticker=ticker,
                    action=action,
                    contract_id=script["contract_id"] if script else None,
                    reasoning=None,
                    confidence=None,
                    validator_status=ValidatorStatus(
                        script.get("validator_status", "accepted") if script else "accepted"
                    ),
                    rejection_reason=script.get("rejection_reason") if script else None,
                )
                session.add(decision)
                session.flush()
                if action != Action.NO_TRADE:
                    result = open_position(session, gateway, decision, as_of=day)
                    if isinstance(result, Rejected):
                        unfilled.append(result)

        mark_positions(session, gateway, day)
        close_positions(session, gateway, day)
        evaluate_closed_positions(session)
        run.status = RunStatus.COMPLETED
        session.flush()
    return unfilled


def test_known_answers_match_to_the_cent(db_session_factory: sessionmaker[Session]) -> None:
    fixture = _load()
    start = dt.date.fromisoformat(fixture["start"])
    end = dt.date.fromisoformat(fixture["end"])

    with db_session_factory() as session:
        unfilled = _run_month(session, fixture)
        session.commit()

        assert [r.reason for r in unfilled] == [u["reason"] for u in fixture["unfilled"]]

        for cohort_name, expected in fixture["expected"].items():
            m = cohort_metrics(session, Cohort(cohort_name), start, end)
            assert m.decisions == expected["decisions"], cohort_name
            assert m.no_trade_count == expected["no_trade_count"], cohort_name
            assert m.trades == expected["trades"], cohort_name
            assert m.hit_rate == Decimal(expected["hit_rate"]), cohort_name
            assert m.mean_pnl == Decimal(expected["mean_pnl"]), cohort_name
            assert m.median_pnl == Decimal(expected["median_pnl"]), cohort_name
            assert m.total_pnl == Decimal(expected["total_pnl"]), cohort_name
            assert m.max_drawdown == Decimal(expected["max_drawdown"]), cohort_name
            assert m.pnl_vs_cash == Decimal(expected["pnl_vs_cash"]), cohort_name

        rows = session.execute(
            select(PaperPosition, Evaluation, Decision.ticker)
            .join(Evaluation, Evaluation.position_id == PaperPosition.id)
            .join(Decision, Decision.id == PaperPosition.decision_id)
            .order_by(PaperPosition.opened_at, PaperPosition.id)
        ).all()
        assert len(rows) == len(fixture["trades"])
        pairs = zip(rows, fixture["trades"], strict=True)
        for (position, evaluation, ticker), expected_trade in pairs:
            assert position.cohort.value == expected_trade["cohort"]
            assert ticker == expected_trade["ticker"]
            assert position.contract_id == expected_trade["contract_id"]
            assert position.opened_at.date() == dt.date.fromisoformat(expected_trade["opened"])
            assert position.closed_at is not None
            assert position.closed_at.date() == dt.date.fromisoformat(expected_trade["closed"])
            assert position.open_price == Decimal(expected_trade["open_price"])
            assert position.close_price == Decimal(expected_trade["close_price"])
            assert position.underlying_open == Decimal(expected_trade["underlying_open"])
            assert position.underlying_close == Decimal(expected_trade["underlying_close"])
            assert evaluation.realized_pnl == Decimal(expected_trade["realized_pnl"])
            assert evaluation.direction_correct is expected_trade["direction_correct"]
            assert evaluation.horizon_days == expected_trade["horizon_days"]


def test_cohort_metrics_returns_zeros_with_no_data(
    db_session_factory: sessionmaker[Session],
) -> None:
    with db_session_factory() as session:
        m = cohort_metrics(session, Cohort.B, dt.date(1999, 1, 1), dt.date(1999, 1, 31))
    assert (m.decisions, m.no_trade_count, m.trades) == (0, 0, 0)
    assert m.hit_rate == 0
    assert m.mean_pnl == m.median_pnl == m.total_pnl == m.max_drawdown == m.pnl_vs_cash == 0
