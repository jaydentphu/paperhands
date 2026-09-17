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
"""

from __future__ import annotations

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
