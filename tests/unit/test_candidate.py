from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from src.agent.schema import TradeCandidate
from src.models import ContractSnapshot
from src.models.enums import ContractType
from src.validator.candidate import (
    ACTION_CONTRACT_TYPE_MISMATCH,
    CONTRACT_NOT_ELIGIBLE,
    MAX_LOSS_EXCEEDS_CAP,
    SCHEMA_INVALID,
    TICKER_OFF_WATCHLIST,
    Accepted,
    Rejected,
    validate_candidate,
)

EXPIRY = dt.date(2026, 10, 16)


def _contract(contract_id: str, contract_type: ContractType, ask: Decimal) -> ContractSnapshot:
    return ContractSnapshot(
        snapshot_id=1,
        contract_id=contract_id,
        contract_type=contract_type,
        strike=Decimal("150"),
        expiry=EXPIRY,
        bid=ask - Decimal("0.20"),
        ask=ask,
        volume=100,
        open_interest=1000,
        implied_vol=Decimal("0.3"),
        eligible=True,
        ineligible_reason=None,
    )


CALL = _contract("call-1", ContractType.CALL, Decimal("2.20"))
PUT = _contract("put-1", ContractType.PUT, Decimal("2.20"))
EXPENSIVE_CALL = _contract("call-expensive", ContractType.CALL, Decimal("4.00"))


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ticker": "AAPL",
        "action": "long_call",
        "contract_id": "call-1",
        "thesis": "Momentum is bullish into earnings.",
        "evidence_for": ["20-day return is positive", "RSI above 55"],
        "evidence_against": ["IV is elevated", "Broad market is choppy"],
        "confidence": 0.7,
        "invalidation": "Price closes below the 20-day moving average.",
    }
    payload.update(overrides)
    return payload


def test_accepted_long_call() -> None:
    result = validate_candidate(_payload(), [CALL, PUT])
    assert isinstance(result, Accepted)
    assert result.contract is CALL
    assert result.max_loss == Decimal("220.00")


def test_accepted_no_trade_has_no_contract_or_max_loss() -> None:
    result = validate_candidate(_payload(action="no_trade", contract_id=None), [CALL, PUT])
    assert isinstance(result, Accepted)
    assert result.contract is None
    assert result.max_loss is None


def test_rejects_invalid_schema() -> None:
    result = validate_candidate(_payload(confidence=1.5), [CALL, PUT])
    assert result == Rejected(SCHEMA_INVALID)


def test_rejects_ticker_off_watchlist() -> None:
    result = validate_candidate(_payload(ticker="TSLA"), [CALL, PUT])
    assert result == Rejected(TICKER_OFF_WATCHLIST)


def test_rejects_contract_not_eligible() -> None:
    result = validate_candidate(_payload(contract_id="not-in-list"), [CALL, PUT])
    assert result == Rejected(CONTRACT_NOT_ELIGIBLE)


def test_rejects_action_contract_type_mismatch() -> None:
    result = validate_candidate(_payload(action="long_call", contract_id="put-1"), [CALL, PUT])
    assert result == Rejected(ACTION_CONTRACT_TYPE_MISMATCH)


def test_rejects_max_loss_exceeds_cap() -> None:
    result = validate_candidate(_payload(contract_id="call-expensive"), [EXPENSIVE_CALL])
    assert result == Rejected(MAX_LOSS_EXCEEDS_CAP)


def test_accepts_an_already_validated_trade_candidate() -> None:
    candidate = TradeCandidate.model_validate(_payload())
    result = validate_candidate(candidate, [CALL, PUT])
    assert isinstance(result, Accepted)
    assert result.candidate is candidate
