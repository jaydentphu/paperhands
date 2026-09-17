"""Per-cohort, per-ticker decision logic, called by daily_run inside that
cohort's own transaction (see daily_run.py). All three share one signature
so daily_run can iterate over them uniformly, even though Cohort A ignores
most of the arguments and Cohort B ignores `messages`/`model`.

Both B and C read spot price and earnings_date from the ticker's stored
Snapshot row (not a fresh gateway call) so every cohort scores the same
run against the same numbers; only historicals are fetched live, since
they aren't stored anywhere.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agent.bundle import build_bundle
from src.agent.runner import AgentRunner, MessagesAPI
from src.gateway import DataGateway
from src.logging import RunLogger
from src.models import Decision, Snapshot
from src.models.enums import Action, Cohort, LogLevel, ValidatorStatus
from src.portfolio import Rejected, open_position
from src.scheduler.run_agent import HISTORICAL_DAYS, bundle_inputs_for_snapshot
from src.screener.cash import decide as decide_cash
from src.screener.indicators import RETURN_WINDOW, RSI_PERIOD
from src.screener.screener import ScreenerDecision, screen
from src.validator.candidate import Accepted, validate_candidate
from src.validator.eligibility import eligible_contracts


def _snapshot_for(session: Session, run_id: int, ticker: str) -> Snapshot:
    snapshot = session.scalar(
        select(Snapshot).where(Snapshot.run_id == run_id, Snapshot.ticker == ticker)
    )
    assert snapshot is not None, f"no snapshot for {ticker} in run {run_id}"
    return snapshot


def _maybe_open(
    session: Session,
    gateway: DataGateway,
    decision: Decision,
    as_of: dt.date,
    run_logger: RunLogger,
) -> None:
    if decision.validator_status != ValidatorStatus.ACCEPTED or decision.action == Action.NO_TRADE:
        return
    result = open_position(session, gateway, decision, as_of=as_of)
    if isinstance(result, Rejected):
        run_logger.log(
            LogLevel.WARNING,
            "portfolio",
            f"fill rejected for {decision.ticker} ({decision.action.value}): {result.reason}",
            {"decision_id": decision.id, "contract_id": decision.contract_id},
        )


def run_cohort_a(
    session: Session,
    gateway: DataGateway,
    messages: MessagesAPI,
    run_id: int,
    ticker: str,
    as_of: dt.date,
    model: str,
) -> Decision:
    action = decide_cash()
    decision = Decision(
        run_id=run_id,
        cohort=Cohort.A,
        ticker=ticker,
        action=action,
        contract_id=None,
        reasoning=None,
        confidence=None,
        validator_status=ValidatorStatus.ACCEPTED,
        rejection_reason=None,
    )
    session.add(decision)
    session.flush()
    return decision


def run_cohort_b(
    session: Session,
    gateway: DataGateway,
    messages: MessagesAPI,
    run_id: int,
    ticker: str,
    as_of: dt.date,
    model: str,
) -> Decision:
    snapshot = _snapshot_for(session, run_id, ticker)
    eligible = eligible_contracts(session, run_id, ticker)
    bars = gateway.get_historicals(ticker, HISTORICAL_DAYS)
    spot = Decimal(snapshot.quote["last"])

    if len(bars) > max(RETURN_WINDOW, RSI_PERIOD):
        result = screen(bars, eligible, spot, as_of, snapshot.earnings_date)
    else:
        result = ScreenerDecision(Action.NO_TRADE, None)

    decision = Decision(
        run_id=run_id,
        cohort=Cohort.B,
        ticker=ticker,
        action=result.action,
        contract_id=result.contract.contract_id if result.contract else None,
        reasoning=None,
        confidence=None,
        validator_status=ValidatorStatus.ACCEPTED,
        rejection_reason=None,
    )
    session.add(decision)
    session.flush()
    _maybe_open(session, gateway, decision, as_of, RunLogger(session, run_id))
    return decision


def run_cohort_c(
    session: Session,
    gateway: DataGateway,
    messages: MessagesAPI,
    run_id: int,
    ticker: str,
    as_of: dt.date,
    model: str,
) -> Decision:
    snapshot = _snapshot_for(session, run_id, ticker)
    bundle_inputs, eligible = bundle_inputs_for_snapshot(session, gateway, snapshot, as_of)
    bundle_text = build_bundle(bundle_inputs)
    run_logger = RunLogger(session, run_id)

    runner = AgentRunner(messages, gateway, run_logger, model=model)
    outcome = runner.run(ticker, bundle_text)

    if outcome.candidate is None:
        decision = Decision(
            run_id=run_id,
            cohort=Cohort.C,
            ticker=ticker,
            action=Action.NO_TRADE,
            contract_id=None,
            reasoning=None,
            confidence=None,
            validator_status=ValidatorStatus.REJECTED,
            rejection_reason=outcome.rejection_reason,
        )
        session.add(decision)
        session.flush()
        return decision

    candidate = outcome.candidate
    reasoning = {
        "thesis": candidate.thesis,
        "evidence_for": candidate.evidence_for,
        "evidence_against": candidate.evidence_against,
        "invalidation": candidate.invalidation,
    }
    verdict = validate_candidate(candidate, eligible)
    if isinstance(verdict, Accepted):
        decision = Decision(
            run_id=run_id,
            cohort=Cohort.C,
            ticker=ticker,
            action=candidate.action,
            contract_id=candidate.contract_id,
            reasoning=reasoning,
            confidence=candidate.confidence,
            validator_status=ValidatorStatus.ACCEPTED,
            rejection_reason=None,
        )
    else:
        run_logger.log(
            LogLevel.WARNING,
            "validator",
            f"rejected candidate for {ticker}: {verdict.reason}",
            {"contract_id": candidate.contract_id},
        )
        decision = Decision(
            run_id=run_id,
            cohort=Cohort.C,
            ticker=ticker,
            action=Action.NO_TRADE,
            contract_id=None,
            reasoning=reasoning,
            confidence=candidate.confidence,
            validator_status=ValidatorStatus.REJECTED,
            rejection_reason=verdict.reason,
        )
    session.add(decision)
    session.flush()
    _maybe_open(session, gateway, decision, as_of, run_logger)
    return decision
