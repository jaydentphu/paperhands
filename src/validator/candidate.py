"""Deterministic acceptance/rejection of a TradeCandidate. Takes the raw
candidate payload (whatever the LLM or a screener produced) plus the eligible
contracts for that candidate's ticker in this run - the caller is
responsible for scoping eligible_contracts to the right ticker (one context
bundle per ticker, PRD.md section 3), since ContractSnapshot itself has no
ticker column (it belongs to Snapshot, one level up).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from src.agent.schema import TradeCandidate
from src.config import MAX_PREMIUM, WATCHLIST
from src.models import ContractSnapshot
from src.models.enums import Action, ContractType

SCHEMA_INVALID = "schema_invalid"
TICKER_OFF_WATCHLIST = "ticker_off_watchlist"
CONTRACT_NOT_ELIGIBLE = "contract_not_eligible"
ACTION_CONTRACT_TYPE_MISMATCH = "action_contract_type_mismatch"
MAX_LOSS_EXCEEDS_CAP = "max_loss_exceeds_cap"

_ACTION_CONTRACT_TYPE = {
    Action.LONG_CALL: ContractType.CALL,
    Action.LONG_PUT: ContractType.PUT,
}


@dataclass(frozen=True)
class Accepted:
    candidate: TradeCandidate
    contract: ContractSnapshot | None
    max_loss: Decimal | None


@dataclass(frozen=True)
class Rejected:
    reason: str


ValidationResult = Accepted | Rejected


def validate_candidate(
    raw: dict[str, Any] | TradeCandidate,
    eligible_contracts: list[ContractSnapshot],
) -> ValidationResult:
    if isinstance(raw, TradeCandidate):
        candidate = raw
    else:
        try:
            candidate = TradeCandidate.model_validate(raw)
        except ValidationError:
            return Rejected(SCHEMA_INVALID)

    if candidate.ticker not in WATCHLIST:
        return Rejected(TICKER_OFF_WATCHLIST)

    if candidate.action == Action.NO_TRADE:
        return Accepted(candidate=candidate, contract=None, max_loss=None)

    # TradeCandidate's own validator guarantees contract_id is set whenever
    # action isn't no_trade.
    assert candidate.contract_id is not None
    by_id = {c.contract_id: c for c in eligible_contracts}
    contract = by_id.get(candidate.contract_id)
    if contract is None:
        return Rejected(CONTRACT_NOT_ELIGIBLE)

    if contract.contract_type != _ACTION_CONTRACT_TYPE[candidate.action]:
        return Rejected(ACTION_CONTRACT_TYPE_MISMATCH)

    max_loss = contract.ask * 100
    if max_loss > MAX_PREMIUM:
        return Rejected(MAX_LOSS_EXCEEDS_CAP)

    return Accepted(candidate=candidate, contract=contract, max_loss=max_loss)
