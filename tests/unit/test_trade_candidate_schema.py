from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.agent.schema import TradeCandidate
from src.models.enums import Action


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ticker": "AAPL",
        "action": "long_call",
        "contract_id": "abc123",
        "thesis": "Bullish momentum going into earnings.",
        "evidence_for": ["a", "b"],
        "evidence_against": ["c", "d"],
        "confidence": 0.6,
        "invalidation": "Price breaks below support.",
    }
    payload.update(overrides)
    return payload


def test_valid_long_call() -> None:
    candidate = TradeCandidate.model_validate(_payload())
    assert candidate.action == Action.LONG_CALL
    assert candidate.contract_id == "abc123"


def test_no_trade_with_contract_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(action="no_trade"))


def test_no_trade_without_contract_id_is_valid() -> None:
    candidate = TradeCandidate.model_validate(_payload(action="no_trade", contract_id=None))
    assert candidate.contract_id is None


def test_long_trade_without_contract_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(contract_id=None))


def test_confidence_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(confidence=1.1))
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(confidence=-0.1))


def test_evidence_lists_must_have_two_to_four_items() -> None:
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(evidence_for=["only one"]))
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(evidence_for=["a", "b", "c", "d", "e"]))


def test_unknown_action_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(action="short_call"))


def test_blank_thesis_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeCandidate.model_validate(_payload(thesis=""))
