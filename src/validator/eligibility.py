"""PRD.md section 4 eligibility rules, checked in the order the PRD lists
them: DTE window, spread %, open interest, premium cap. Overwrites the
"pending_eligibility" placeholder Stage 2's snapshot job leaves on every
stored contract.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import DTE_MAX, DTE_MIN, MAX_PREMIUM, MAX_SPREAD_PCT, MIN_OPEN_INTEREST
from src.models import ContractSnapshot, Snapshot

DTE_OUT_OF_WINDOW = "dte_out_of_window"
SPREAD_TOO_WIDE = "spread_too_wide"
OPEN_INTEREST_TOO_LOW = "open_interest_too_low"
PREMIUM_TOO_HIGH = "premium_too_high"


def evaluate_contract(
    *,
    dte: int,
    bid: Decimal,
    ask: Decimal,
    open_interest: int,
    dte_min: int = DTE_MIN,
    dte_max: int = DTE_MAX,
    max_spread_pct: Decimal = MAX_SPREAD_PCT,
    min_open_interest: int = MIN_OPEN_INTEREST,
    max_premium: Decimal = MAX_PREMIUM,
) -> tuple[bool, str | None]:
    if not dte_min <= dte <= dte_max:
        return False, DTE_OUT_OF_WINDOW

    mid = (bid + ask) / 2
    if mid <= 0 or (ask - bid) / mid > max_spread_pct:
        return False, SPREAD_TOO_WIDE

    if open_interest < min_open_interest:
        return False, OPEN_INTEREST_TOO_LOW

    if ask * 100 > max_premium:
        return False, PREMIUM_TOO_HIGH

    return True, None


def apply_eligibility(session: Session, run_id: int, as_of: dt.date) -> int:
    """Marks every contract_snapshot for this run eligible/ineligible. Does
    not commit - the caller controls the transaction boundary."""
    contracts = session.scalars(
        select(ContractSnapshot)
        .join(Snapshot, Snapshot.id == ContractSnapshot.snapshot_id)
        .where(Snapshot.run_id == run_id)
    ).all()
    for contract in contracts:
        dte = (contract.expiry - as_of).days
        eligible, reason = evaluate_contract(
            dte=dte, bid=contract.bid, ask=contract.ask, open_interest=contract.open_interest
        )
        contract.eligible = eligible
        contract.ineligible_reason = reason
    return len(contracts)


def eligible_contracts(session: Session, run_id: int, ticker: str) -> list[ContractSnapshot]:
    return list(
        session.scalars(
            select(ContractSnapshot)
            .join(Snapshot, Snapshot.id == ContractSnapshot.snapshot_id)
            .where(
                Snapshot.run_id == run_id,
                Snapshot.ticker == ticker,
                ContractSnapshot.eligible.is_(True),
            )
        ).all()
    )
