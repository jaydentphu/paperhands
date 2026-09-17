"""TradeCandidate: the agent's only output, PRD.md section 6, enforced with
Pydantic. Created in Stage 3 (not Stage 4) because src/validator/candidate.py
needs it to exist before the agent that produces it does. Stage 4 builds the
bundle/prompt/runner around this schema without redefining it.

Self-contained field constraints live here (types, ranges, list lengths,
contract_id required iff a trade is being made). Constraints that need
run-time context - watchlist membership, contract eligibility, action vs.
contract type, the max-loss cap - are src/validator/candidate.py's job
(CLAUDE.md rule 4: the agent never computes money, and never decides
eligibility either).

OUTPUT_SCHEMA is the JSON schema handed to the API's structured-output
format. It is written by hand, restricted to the keywords structured
outputs supports (no min/max lengths or numeric bounds), and kept in sync
with the model by a test. The Pydantic model remains the enforcement point.
"""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, Field, model_validator

from src.models.enums import Action


class TradeCandidate(BaseModel):
    ticker: str
    action: Action
    contract_id: str | None = None
    thesis: str = Field(min_length=1)
    evidence_for: list[str] = Field(min_length=2, max_length=4)
    evidence_against: list[str] = Field(min_length=2, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)
    invalidation: str = Field(min_length=1)

    @model_validator(mode="after")
    def contract_id_matches_action(self) -> TradeCandidate:
        if self.action == Action.NO_TRADE:
            if self.contract_id is not None:
                raise ValueError("contract_id must be None when action is no_trade")
        elif self.contract_id is None:
            raise ValueError("contract_id is required when action is long_call or long_put")
        return self


OUTPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "ticker": {"type": "string"},
        "action": {"type": "string", "enum": [a.value for a in Action]},
        "contract_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "thesis": {"type": "string"},
        "evidence_for": {"type": "array", "items": {"type": "string"}},
        "evidence_against": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "invalidation": {"type": "string"},
    },
    "required": [
        "ticker",
        "action",
        "contract_id",
        "thesis",
        "evidence_for",
        "evidence_against",
        "confidence",
        "invalidation",
    ],
    "additionalProperties": False,
}
