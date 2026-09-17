"""open_position: fills one contract at the current ask, re-checking
eligibility against the live chain rather than the (possibly stale)
snapshot - PRD.md section 4: "Position rejected if contract fails
eligibility at fill time." Quantity is always 1 and max_loss is always
ask x 100 (CLAUDE.md rule 4: this file, not the agent, computes money).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import market_today
from src.gateway import DataGateway
from src.models import Decision, PaperPosition
from src.models.enums import Action, ContractType, PositionStatus
from src.portfolio.contracts import fetch_chain_lookup
from src.validator.eligibility import evaluate_contract

CONTRACT_NOT_FOUND = "contract_not_found"
POSITION_ALREADY_OPEN = "position_already_open_for_ticker"

_ACTION_CONTRACT_TYPE = {
    Action.LONG_CALL: ContractType.CALL,
    Action.LONG_PUT: ContractType.PUT,
}


@dataclass(frozen=True)
class Opened:
    position: PaperPosition


@dataclass(frozen=True)
class Rejected:
    reason: str


OpenResult = Opened | Rejected


def _has_open_position_for_ticker(session: Session, cohort: str, ticker: str) -> bool:
    existing = session.scalar(
        select(PaperPosition.id)
        .join(Decision, Decision.id == PaperPosition.decision_id)
        .where(
            PaperPosition.cohort == cohort,
            Decision.ticker == ticker,
            PaperPosition.status == PositionStatus.OPEN,
        )
    )
    return existing is not None


def open_position(
    session: Session,
    gateway: DataGateway,
    decision: Decision,
    as_of: dt.date | None = None,
) -> OpenResult:
    if decision.action == Action.NO_TRADE or decision.contract_id is None:
        raise ValueError(
            "open_position requires a long_call/long_put decision with a contract_id"
        )
    as_of = as_of or market_today()

    # Deferred from the Stage 4 strategy review (see NOTES.md): at most one
    # open position per cohort per ticker, so a persistent signal can't
    # create several overlapping positions on the same underlying.
    if _has_open_position_for_ticker(session, decision.cohort, decision.ticker):
        return Rejected(POSITION_ALREADY_OPEN)

    chain = fetch_chain_lookup(gateway, decision.ticker)
    contract = chain.get(decision.contract_id)
    if contract is None or contract.contract_type != _ACTION_CONTRACT_TYPE[decision.action]:
        return Rejected(CONTRACT_NOT_FOUND)

    dte = contract.dte(as_of)
    eligible, reason = evaluate_contract(
        dte=dte, bid=contract.bid, ask=contract.ask, open_interest=contract.open_interest
    )
    if not eligible:
        assert reason is not None
        return Rejected(reason)

    position = PaperPosition(
        cohort=decision.cohort,
        decision_id=decision.id,
        contract_id=contract.contract_id,
        expiry=contract.expiry,
        opened_at=dt.datetime.now(dt.UTC),
        open_price=contract.ask,
        quantity=1,
        max_loss=contract.ask * 100,
        status=PositionStatus.OPEN,
    )
    session.add(position)
    session.flush()
    return Opened(position)
