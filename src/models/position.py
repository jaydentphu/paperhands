from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.enums import CloseReason, Cohort, PositionStatus


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort: Mapped[Cohort] = mapped_column(Enum(Cohort, name="cohort"), nullable=False)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    max_loss: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus, name="position_status"), nullable=False, default=PositionStatus.OPEN
    )
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    close_reason: Mapped[CloseReason | None] = mapped_column(
        Enum(CloseReason, name="close_reason"), nullable=True
    )
