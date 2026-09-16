from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.enums import Action, Cohort, ValidatorStatus


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    cohort: Mapped[Cohort] = mapped_column(Enum(Cohort, name="cohort"), nullable=False)
    ticker: Mapped[str] = mapped_column(
        String(10), ForeignKey("watchlist_symbols.ticker"), nullable=False
    )
    action: Mapped[Action] = mapped_column(Enum(Action, name="action"), nullable=False)
    contract_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Bundles thesis, evidence_for, evidence_against, invalidation from
    # PRD section 6's TradeCandidate - Cohort C only, null for A/B.
    reasoning: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    validator_status: Mapped[ValidatorStatus] = mapped_column(
        Enum(ValidatorStatus, name="validator_status"), nullable=False
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
